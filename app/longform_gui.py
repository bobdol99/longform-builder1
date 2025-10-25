#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, re, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from dataclasses import dataclass
from typing import List, Dict, Any
from PIL import Image, ImageTk
import numpy as np

# ---------------------------------------------------------
# 📸 썸네일 이미지 분석 함수
# ---------------------------------------------------------
def _to_rgb(img):
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img

def analyze_thumbnail_image(pil_image):
    img = _to_rgb(pil_image)
    base = 512
    w, h = img.size
    scale = base / max(w, h)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.BICUBIC)
    arr = np.asarray(img).astype(np.float32) / 255.0
    luma = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    contrast_std = float(np.std(luma) * 100.0)

    # 간단한 엣지 계산 (Sobel)
    Kx = np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]], dtype=np.float32)
    Ky = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], dtype=np.float32)
    gp = np.pad(luma, ((1, 1), (1, 1)), mode="edge")
    Gx = (
        Kx[0, 0] * gp[:-2, :-2] + Kx[0, 1] * gp[:-2, 1:-1] + Kx[0, 2] * gp[:-2, 2:] +
        Kx[1, 0] * gp[1:-1, :-2] + Kx[1, 1] * gp[1:-1, 1:-1] + Kx[1, 2] * gp[1:-1, 2:] +
        Kx[2, 0] * gp[2:, :-2] + Kx[2, 1] * gp[2:, 1:-1] + Kx[2, 2] * gp[2:, 2:]
    )
    Gy = (
        Ky[0, 0] * gp[:-2, :-2] + Ky[0, 1] * gp[:-2, 1:-1] + Ky[0, 2] * gp[:-2, 2:] +
        Ky[1, 0] * gp[1:-1, :-2] + Ky[1, 1] * gp[1:-1, 1:-1] + Ky[1, 2] * gp[1:-1, 2:] +
        Ky[2, 0] * gp[2:, :-2] + Ky[2, 1] * gp[2:, 1:-1] + Ky[2, 2] * gp[2:, 2:]
    )
    grad = np.sqrt(Gx ** 2 + Gy ** 2)
    thresh = max(0.2, float(np.mean(grad) + 1.5 * np.std(grad)))
    edge_density = float((grad > thresh).mean())

    white_ratio = float((luma > 0.85).mean())
    black_ratio = float((luma < 0.15).mean())

    mean_rgb = np.mean(arr.reshape(-1, 3), axis=0)
    red_dom = mean_rgb[0] > 0.4 and mean_rgb[0] > mean_rgb[1] + 0.05 and mean_rgb[0] > mean_rgb[2] + 0.05
    yellow_dom = (mean_rgb[0] > 0.45 and mean_rgb[1] > 0.45 and mean_rgb[2] < 0.3)
    blue_dom = mean_rgb[2] > 0.4 and mean_rgb[2] > mean_rgb[1] + 0.05 and mean_rgb[2] > mean_rgb[0] + 0.05
    color_pop = any([red_dom, yellow_dom, blue_dom])

    import colorsys
    hsv = np.array([colorsys.rgb_to_hsv(*px) for px in arr.reshape(-1, 3)], dtype=np.float32)
    H, S, V = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    skin_mask = (((H >= 0.0) & (H <= 0.14)) | (H >= 0.9)) & (S >= 0.1) & (S <= 0.7) & (V >= 0.2) & (V <= 0.95)
    skin_ratio = float(skin_mask.mean())

    cues = {
        "face_closeup_proxy": skin_ratio >= 0.12,
        "contrast": contrast_std >= 12.0,
        "big_text_proxy": (white_ratio > 0.12 or black_ratio > 0.12),
        "color_pop": color_pop
    }
    score = int(cues["face_closeup_proxy"]) + int(cues["contrast"]) + int(cues["big_text_proxy"]) + int(cues["color_pop"])
    if edge_density > 0.08:
        score += 1
    score = max(0, min(5, score))
    return {
        "metrics": {
            "contrast_std": round(contrast_std, 2),
            "edge_density": round(edge_density, 4),
            "white_ratio": round(white_ratio, 4),
            "black_ratio": round(black_ratio, 4),
            "skin_ratio": round(skin_ratio, 4),
        },
        "salience_score_0_5": score
    }

# ---------------------------------------------------------
# 🧠 텍스트/스크립트 분석 유틸
# ---------------------------------------------------------
@dataclass
class ReferenceVideoInput:
    views: int
    likes: int
    seconds: int
    title: str
    thumbnail: str
    script_text: str

def safe_div(a, b):
    return a / b if b else 0

def analyze_reference(ref: ReferenceVideoInput):
    title_keywords = [w for w in re.findall(r"[가-힣A-Za-z0-9]+", ref.title) if len(w) > 1]
    er = safe_div(ref.likes, ref.views)
    er_tier = "높음(5%+)" if er >= 0.05 else "보통(1~4%)" if er >= 0.01 else "낮음(<1%)"

    thumb_result = {}
    if os.path.isfile(ref.thumbnail):
        try:
            img = Image.open(ref.thumbnail)
            thumb_result = analyze_thumbnail_image(img)
        except Exception as e:
            thumb_result = {"error": str(e)}

    return {
        "title_keywords": title_keywords,
        "engagement_rate": round(er * 100, 2),
        "er_tier": er_tier,
        "thumbnail_analysis": thumb_result,
    }

# ---------------------------------------------------------
# 🎨 Tkinter GUI
# ---------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Longform Script Builder (KR) - 썸네일 이미지 분석")
        self.geometry("1100x750")
        self.build_ui()

    def build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # 탭 구성
        self.tab_input = ttk.Frame(nb)
        self.tab_output = ttk.Frame(nb)
        nb.add(self.tab_input, text="입력")
        nb.add(self.tab_output, text="결과")

        # 입력 영역
        frame = ttk.Frame(self.tab_input)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.var_views = tk.StringVar(value="1000000")
        self.var_likes = tk.StringVar(value="50000")
        self.var_seconds = tk.StringVar(value="600")
        self.var_title = tk.StringVar(value="초보도 되는 10분 정리 루틴")
        self.var_thumb = tk.StringVar()
        ttk.Label(frame, text="조회수").grid(row=0, column=0)
        ttk.Entry(frame, textvariable=self.var_views, width=12).grid(row=0, column=1)
        ttk.Label(frame, text="좋아요수").grid(row=0, column=2)
        ttk.Entry(frame, textvariable=self.var_likes, width=12).grid(row=0, column=3)
        ttk.Label(frame, text="길이(초)").grid(row=0, column=4)
        ttk.Entry(frame, textvariable=self.var_seconds, width=12).grid(row=0, column=5)
        ttk.Label(frame, text="제목").grid(row=1, column=0)
        ttk.Entry(frame, textvariable=self.var_title, width=70).grid(row=1, column=1, columnspan=5, sticky="we")

        ttk.Label(frame, text="썸네일 이미지").grid(row=2, column=0)
        ttk.Entry(frame, textvariable=self.var_thumb, width=60).grid(row=2, column=1, columnspan=4, sticky="we")
        ttk.Button(frame, text="파일 선택", command=self.pick_thumbnail).grid(row=2, column=5)

        ttk.Label(frame, text="스크립트").grid(row=3, column=0, sticky="nw")
        self.txt_script = ScrolledText(frame, height=15, wrap="word")
        self.txt_script.grid(row=3, column=1, columnspan=5, sticky="nsew", pady=5)
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        ttk.Button(frame, text="분석 실행", command=self.run_analysis).grid(row=4, column=5, pady=10)

        # 결과 탭
        self.txt_out = ScrolledText(self.tab_output, height=30, wrap="word")
        self.txt_out.pack(fill="both", expand=True, padx=10, pady=10)

    def pick_thumbnail(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.png *.jpeg *.webp *.bmp")])
        if path:
            self.var_thumb.set(path)

    def run_analysis(self):
        try:
            ref = ReferenceVideoInput(
                views=int(self.var_views.get()),
                likes=int(self.var_likes.get()),
                seconds=int(self.var_seconds.get()),
                title=self.var_title.get(),
                thumbnail=self.var_thumb.get(),
                script_text=self.txt_script.get("1.0", "end").strip()
            )
        except ValueError:
            messagebox.showerror("입력 오류", "숫자 형식을 확인하세요.")
            return

        result = analyze_reference(ref)
        self.txt_out.delete("1.0", "end")
        self.txt_out.insert("end", f"제목 키워드: {', '.join(result['title_keywords'])}\n")
        self.txt_out.insert("end", f"참여율: {result['engagement_rate']}% ({result['er_tier']})\n")

        thumb = result["thumbnail_analysis"]
        if thumb:
            self.txt_out.insert("end", f"\n[썸네일 분석]\n{json.dumps(thumb, ensure_ascii=False, indent=2)}\n")
        else:
            self.txt_out.insert("end", "\n썸네일 이미지가 없습니다.\n")

        messagebox.showinfo("완료", "분석이 완료되었습니다!")

# ---------------------------------------------------------
if __name__ == "__main__":
    App().mainloop()
