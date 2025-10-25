
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Longform Script Builder - GUI (Tkinter, Korean)
-----------------------------------------------
- 입력: 조회수, 좋아요수, 길이(초), 제목, 썸네일 설명, 스크립트
- 출력 A: 성과 분석
- 출력 B: 유사하지만 다른 아이디어 10개
- 출력 C: (옵션) 화자/챕터/영상 톤 입력 시 최종 대본

실행:
$ python longform_gui.py
"""

from __future__ import annotations
import json
import re
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from dataclasses import dataclass
from typing import List, Dict, Any

# ---------- Data Model ----------
@dataclass
class ReferenceVideoInput:
    views: int
    likes: int
    seconds: int
    title: str
    thumbnail: str
    script_text: str

# ---------- Helpers ----------
KOREAN_STOPWORDS = set([
    "그리고","그러나","하지만","또한","그래서","하지만","그런데","또","또는","혹은","이것","저것","그것",
    "정말","진짜","약간","좀","너무","그냥","이번","오늘","영상","시간","여러분"
])

def tokenize_korean(text: str) -> List[str]:
    text = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", text)
    toks = [t for t in text.split() if t]
    return toks

def word_count(text: str) -> int:
    return len(tokenize_korean(text))

def safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        return a / b if b else default
    except ZeroDivisionError:
        return default

def pct(x: float) -> str:
    return f"{x*100:.1f}%"

def mmss(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def top_keywords(text: str, k: int = 8) -> List[str]:
    toks = tokenize_korean(text.lower())
    freq = {}
    for t in toks:
        if t in KOREAN_STOPWORDS or len(t) <= 1:
            continue
        freq[t] = freq.get(t, 0) + 1
    return [w for w,_ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:k]]

def detect_hook(script_text: str) -> Dict[str, Any]:
    first_200 = script_text.strip()[:400]
    signals = [
        ("숫자/기간", re.search(r"\b\d+\s*(초|분|시간|일|주|개월|년)\b", first_200) is not None),
        ("강한감정", any(kw in first_200 for kw in ["충격", "소름", "몰랐던", "반전", "최강", "필수"])),
        ("대비/갈등", any(kw in first_200 for kw in ["하지만", "문제는", "대신", "vs", "반면"])),
        ("시청자호출", any(kw in first_200 for kw in ["여러분", "당신", "지금", "꼭"])),
        ("약속/혜택", any(kw in first_200 for kw in ["방법", "꿀팁", "비법", "정리", "가이드", "무료"])),
    ]
    score = sum(1 for _, ok in signals if ok)
    return {
        "hook_preview": first_200.replace("\n"," ")[:120] + ("..." if len(first_200)>120 else ""),
        "signals": {name: ok for name, ok in signals},
        "score_5": score
    }

def estimate_sections(script_text: str) -> Dict[str, Any]:
    markers = re.findall(r"(챕터\s*\d+|파트\s*\d+|^#.+$|^\d+\.\s+.+$|^##\s+.+$)", script_text, flags=re.M)
    return {"estimated_chapters": len(markers), "markers_sample": markers[:5]}

def title_analysis(title: str) -> Dict[str, Any]:
    kws = top_keywords(title, k=10)
    has_number = bool(re.search(r"\d+", title))
    has_duration = bool(re.search(r"\b(초|분|시간|일|주|개월|년)\b", title))
    power_words = ["충격","공개","비밀","실험","테스트","가이드","꿀팁","완벽","긴급","주의"]
    power_hit = sum(1 for w in power_words if w in title)
    specificity = sum([has_number, has_duration]) + min(power_hit,2)
    return {"keywords": kws, "has_number": has_number, "has_duration": has_duration,
            "power_words_hit": power_hit, "specificity_score_0_4": specificity}

def thumbnail_analysis(thumbnail_desc: str) -> Dict[str, Any]:
    cues = {
        "face_closeup": any(k in thumbnail_desc for k in ["얼굴","클로즈업","표정","눈물","웃음","놀람"]),
        "contrast": any(k in thumbnail_desc for k in ["전후","Before","After","비교","대비","VS","vs"]),
        "big_text": any(k in thumbnail_desc for k in ["대문자","굵은","강조","텍스트","숫자"]),
        "object_tool": any(k in thumbnail_desc for k in ["도구","제품","장치","기계","키트","세트"]),
        "color_pop": any(k in thumbnail_desc for k in ["형광","원색","네온","빨강","노랑","파랑"]),
    }
    score = sum(int(v) for v in cues.values())
    return {"cues": cues, "salience_score_0_5": score}

def pacing_analysis(seconds: int, script_text: str) -> Dict[str, Any]:
    words = word_count(script_text)
    wpm = safe_div(words, seconds/60.0, default=0.0)
    if wpm < 120: pace = "느림(서사/설명형 적합)"
    elif wpm < 160: pace = "적정(대부분의 정보/교육형)"
    elif wpm < 200: pace = "조금 빠름(엔터테인/하이라이트)"
    else: pace = "매우 빠름(과밀 가능)"
    return {"words": words, "wpm": round(wpm,1), "pacing_comment": pace}

def engagement_metrics(views: int, likes: int) -> Dict[str, Any]:
    er = safe_div(likes, views, default=0.0)
    tier = "보통(1~4%)"
    if er < 0.01: tier = "낮음(<1%)"
    elif er >= 0.05: tier = "높음(5%+)"
    return {"engagement_rate": round(er,4), "tier": tier}

def analyze_reference(ref: ReferenceVideoInput) -> Dict[str, Any]:
    title_a = title_analysis(ref.title)
    thumb_a = thumbnail_analysis(ref.thumbnail)
    hook_a = detect_hook(ref.script_text)
    pace_a = pacing_analysis(ref.seconds, ref.script_text)
    eng_a = engagement_metrics(ref.views, ref.likes)
    sections_a = estimate_sections(ref.script_text)

    strengths = []
    if hook_a["score_5"] >= 3: strengths.append("시작 20~30초에 강한 훅 신호가 충분함")
    if title_a["specificity_score_0_4"] >= 2: strengths.append("제목에 숫자/기간/파워워드로 구체성 확보")
    if thumb_a["salience_score_0_5"] >= 3: strengths.append("썸네일 대비/객체 강조가 시각적 주목을 끔")
    if eng_a["engagement_rate"] >= 0.05: strengths.append("참여율이 높은 편으로, 공감/실용 포인트가 강함")
    if 120 <= pace_a["wpm"] <= 190: strengths.append("말하기 속도가 적정 범위로 이탈 적음")
    if sections_a["estimated_chapters"] >= 3: strengths.append("챕터 구성이 존재하여 흐름이 명확함")

    risks = []
    if hook_a["score_5"] <= 2: risks.append("오프닝 훅 신호가 약함 → 첫 10초 개선 필요")
    if title_a["power_words_hit"] == 0 and not title_a["has_number"]:
        risks.append("제목의 자극/구체 신호 부족 → 숫자/기간/결과를 노출")
    if pace_a["wpm"] > 200: risks.append("발화 밀도 과다 → 컷어웨이와 휴지점 필요")
    if thumb_a["salience_score_0_5"] <= 2: risks.append("썸네일 임팩트 약함 → 대비/표정/대형 숫자 활용")
    if eng_a["engagement_rate"] < 0.01: risks.append("참여율 낮음 → 챕터별 질문/댓글 유도 장치 추가")

    why_high = [
        "훅-제목-썸네일이 일관되게 같은 약속을 전달",
        "정보 밀도와 컷 전환이 지루함을 방지",
        "문제-해결 구조로 즉시적 효용을 약속",
        "명확한 대상(페르소나) 지정을 통해 공감 강화"
    ]

    return {
        "summary": {
            "runtime": mmss(ref.seconds),
            "engagement": eng_a,
            "pacing": pace_a,
            "title": title_a,
            "thumbnail": thumb_a,
            "hook": hook_a,
            "sections": sections_a,
        },
        "strengths": strengths,
        "risks": risks,
        "why_it_performed": why_high
    }

# ---------- Idea Generation ----------
BASE_ANGLES = [
    ("실험/챌린지", "정해진 시간/예산/도구 제한으로 실험"),
    ("룰브레이킹", "통념/잘못된 루틴을 깨고 검증"),
    ("집중공략", "한 요소만 극한으로 최적화"),
    ("케이스스터디", "성공/실패 사례를 해부"),
    ("스토리텔링", "개인사/갈등-반전 구조"),
    ("비교/대결", "A/B 대결과 승자 선정"),
    ("트러블슈팅", "실패 원인 10가지와 해결"),
    ("원리/해부", "메커니즘/심리학으로 설명"),
    ("속도런", "X분만에 결과 내기"),
    ("미니시리즈", "Part1~3 연속 구성")
]

DIFF_VAULT = [
    "현장 오디오+자막 동시 노출",
    "댓글 미션 채택 후 실험",
    "장비 1개만 허용",
    "예산 상한선 1만원",
    "주요 장면은 2배속 타임랩스",
    "실패율 공개(%)와 재도전",
    "전문가/비전문가 동시 테스트",
    "청각/무자막 접근성 버전 동시 제공",
    "챕터별 체크리스트 PDF 제공",
    "실시간 타이머/카운터 노출"
]

def generate_ideas(ref: ReferenceVideoInput, n: int = 10) -> List[Dict[str,str]]:
    base_kw = top_keywords(ref.title + " " + ref.script_text, k=6)
    results = []
    for i in range(n):
        angle = BASE_ANGLES[i % len(BASE_ANGLES)]
        diff = DIFF_VAULT[i % len(DIFF_VAULT)]
        idea_title = f"[{angle[0]}] {', '.join(base_kw[:3])}를 {['다르게','극한으로','반대로','제로베이스'][i%4]} 해봤다"
        concept = f"{angle[1]} + 차별포인트: {diff}"
        logline = f"레퍼런스의 핵심 주제({', '.join(base_kw)})를 유지하되, {angle[0]} 톤으로 전개. {diff} 적용."
        results.append({"idea_title": idea_title, "concept": concept, "logline": logline})
    return results

def auto_outline_from_idea(idea_title: str) -> List[str]:
    return [
        "Hook(문제 제기/약속)",
        "컨텍스트(대상/조건 명시)",
        "본 실험/전개(파트1)",
        "본 실험/전개(파트2)",
        "결과/교훈",
        "CTA(구독/댓글 유도)"
    ]

def generate_script(idea: Dict[str,str], speaker: str, chapters: List[str], filming_style: str) -> str:
    title = idea.get("idea_title","새 아이디어")
    logline = idea.get("logline","")
    lines = []
    lines.append(f"# 최종 대본: {title}\n")
    lines.append(f"## 연출 톤: {filming_style}")
    lines.append(f"## 화자 페르소나: {speaker}")
    lines.append(f"## 로그라인: {logline}\n")

    persona_openers = {
        "전문가":"정확한 데이터와 근거로 안내할게요.",
        "친구":"솔직하게, 편하게 이야기해볼게요.",
        "엄마 크리에이터":"생활 감각으로 딱 필요한 부분만 콕 집어줄게요.",
        "교사":"핵심만 단계별로 정리해 드릴게요.",
        "리포터":"현장감 있게 빠르게 전달합니다.",
    }
    opener = persona_openers.get(speaker, "톤은 자연스럽고 명료합니다.")

    for idx, ch in enumerate(chapters, start=1):
        lines.append(f"\n### 챕터 {idx}. {ch}")
        if idx == 1:
            lines.append(f"내레이션: ({speaker}) {opener} 오늘은 '{title}' 컨셉으로, 실행하면 바로 효과를 확인할 수 있게 준비했어요.")
            lines.append("화면: 강한 B-roll/텍스트 오버레이로 핵심 약속 1문장.")
        elif "컨텍스트" in ch or "컨텍" in ch:
            lines.append("내레이션: 대상, 조건, 제한(시간/예산/장비 1개)을 명확히 선언합니다.")
            lines.append("화면: 자막으로 조건 요약, 테이블 그래픽 3줄.")
        elif "본 실험" in ch or "전개" in ch or "파트" in ch:
            lines.append("내레이션: 단계별 진행—문제→시도→관찰→메모. 실패 포인트는 즉시 표시.")
            lines.append("화면: 멀티캠 컷, 실시간 타이머, 체크리스트 팝업.")
            lines.append("현장 오디오: 주요 반응은 라이브로 살립니다.")
        elif "결과" in ch or "교훈" in ch or "정리" in ch:
            lines.append("내레이션: 핵심 인사이트 3개를 숫자로 요약. (비용, 시간, 성공률)")
            lines.append("화면: 전/후 비교 2분할, 그래프/숫자 카운터.")
            lines.append("한줄결론: 초보는 A부터, 숙련은 B 조합이 최적.")
        elif "CTA" in ch:
            lines.append("내레이션: '여러분 경험은 어땠나요? 다음엔 무엇을 깰까요?' 댓글 미션 제시.")
            lines.append("화면: 구독/알림/관련 영상 2개 카드.")
        else:
            lines.append("내레이션: 이 챕터의 포인트를 2~3문장으로 또박또박 전달.")
            lines.append("화면: 키워드 2개만 큰 자막으로.")
    return "\n".join(lines)

# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Longform Script Builder (KR)")
        self.geometry("1180x820")
        self.minsize(1000, 720)

        self._build_layout()

    def _build_layout(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.page_input = ttk.Frame(nb)
        self.page_output = ttk.Frame(nb)
        self.page_script = ttk.Frame(nb)

        nb.add(self.page_input, text="입력")
        nb.add(self.page_output, text="분석 & 아이디어")
        nb.add(self.page_script, text="최종 대본")

        # --- 입력 탭 ---
        frm = ttk.Frame(self.page_input)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        # 상단 숫자 입력
        top = ttk.Frame(frm); top.pack(fill="x", pady=5)
        self.var_views = tk.StringVar()
        self.var_likes = tk.StringVar()
        self.var_seconds = tk.StringVar()

        ttk.Label(top, text="조회수").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.var_views, width=15).grid(row=0, column=1, padx=5)

        ttk.Label(top, text="좋아요수").grid(row=0, column=2, sticky="w")
        ttk.Entry(top, textvariable=self.var_likes, width=15).grid(row=0, column=3, padx=5)

        ttk.Label(top, text="영상 길이(초)").grid(row=0, column=4, sticky="w")
        ttk.Entry(top, textvariable=self.var_seconds, width=15).grid(row=0, column=5, padx=5)

        # 제목/썸네일
        mid = ttk.Frame(frm); mid.pack(fill="x", pady=5)
        self.var_title = tk.StringVar()
        ttk.Label(mid, text="영상 제목").grid(row=0, column=0, sticky="w")
        ttk.Entry(mid, textvariable=self.var_title, width=90).grid(row=0, column=1, padx=5, sticky="we")
        mid.grid_columnconfigure(1, weight=1)

        self.var_thumb = tk.StringVar()
        ttk.Label(mid, text="썸네일 설명").grid(row=1, column=0, sticky="w")
        ttk.Entry(mid, textvariable=self.var_thumb, width=90).grid(row=1, column=1, padx=5, sticky="we")

        # 스크립트
        ttk.Label(frm, text="스크립트(대본) 전문").pack(anchor="w")
        self.txt_script = ScrolledText(frm, height=14, wrap="word")
        self.txt_script.pack(fill="both", expand=True, pady=5)

        # 파일 로드/저장 버튼
        btns = ttk.Frame(frm); btns.pack(fill="x")
        ttk.Button(btns, text="JSON 불러오기", command=self.load_json).pack(side="left")
        ttk.Button(btns, text="JSON 저장", command=self.save_json).pack(side="left", padx=6)
        ttk.Button(btns, text="분석 실행(→ '분석 & 아이디어' 탭)", command=self.run_analysis).pack(side="right")

        # --- 분석 & 아이디어 탭 ---
        out = ttk.Frame(self.page_output); out.pack(fill="both", expand=True, padx=10, pady=10)
        self.txt_analysis = ScrolledText(out, height=18, wrap="word")
        self.txt_analysis.pack(fill="x", pady=6)

        # 아이디어 리스트
        ttk.Label(out, text="아이디어(10개)").pack(anchor="w")
        self.tree = ttk.Treeview(out, columns=("title","concept","logline"), show="headings", height=8)
        self.tree.heading("title", text="아이디어 제목")
        self.tree.heading("concept", text="컨셉(차별포인트 포함)")
        self.tree.heading("logline", text="로그라인")
        self.tree.column("title", width=260)
        self.tree.column("concept", width=380)
        self.tree.column("logline", width=380)
        self.tree.pack(fill="both", expand=True)

        idea_btns = ttk.Frame(out); idea_btns.pack(fill="x", pady=5)
        ttk.Button(idea_btns, text="선택 → 대본 탭으로 보내기", command=self.apply_selected_idea).pack(side="right")

        # --- 최종 대본 탭 ---
        scr = ttk.Frame(self.page_script); scr.pack(fill="both", expand=True, padx=10, pady=10)

        ctrl = ttk.Frame(scr); ctrl.pack(fill="x")
        ttk.Label(ctrl, text="화자 페르소나").grid(row=0, column=0, sticky="w")
        self.cbo_speaker = ttk.Combobox(ctrl, values=["전문가","친구","엄마 크리에이터","교사","리포터"], width=14)
        self.cbo_speaker.set("전문가")
        self.cbo_speaker.grid(row=0, column=1, padx=5)

        ttk.Label(ctrl, text="영상 톤/기법").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.cbo_style = ttk.Combobox(ctrl, values=["스튜디오 톤","1인칭 브이로그","현장 리포트"], width=18)
        self.cbo_style.set("스튜디오 톤")
        self.cbo_style.grid(row=0, column=3, padx=5)

        ttk.Label(ctrl, text="챕터(쉼표로 분리)").grid(row=1, column=0, sticky="w", pady=(8,0))
        self.var_chapters = tk.StringVar(value="Hook(문제 제기/약속),컨텍스트(대상/조건 명시),본 실험/전개(파트1),본 실험/전개(파트2),결과/교훈,CTA(구독/댓글 유도)")
        ttk.Entry(ctrl, textvariable=self.var_chapters, width=90).grid(row=1, column=1, columnspan=3, sticky="we", pady=(8,0))

        self.txt_final = ScrolledText(scr, height=22, wrap="word")
        self.txt_final.pack(fill="both", expand=True, pady=8)

        bottom = ttk.Frame(scr); bottom.pack(fill="x")
        ttk.Button(bottom, text="대본 생성", command=self.build_script).pack(side="right")
        ttk.Button(bottom, text="대본 저장(.md/.txt)", command=self.save_script).pack(side="right", padx=6)

        # 상태
        self._ideas = []
        self._selected_idea = None

    # ---------- Actions ----------
    def _collect_input(self) -> ReferenceVideoInput | None:
        try:
            views = int(self.var_views.get().strip())
            likes = int(self.var_likes.get().strip())
            seconds = int(self.var_seconds.get().strip())
            title = self.var_title.get().strip()
            thumb = self.var_thumb.get().strip()
            script_text = self.txt_script.get("1.0", "end").strip()
            if not title or not script_text:
                raise ValueError("제목과 스크립트는 필수입니다.")
            return ReferenceVideoInput(views, likes, seconds, title, thumb, script_text)
        except Exception as e:
            messagebox.showerror("입력 오류", str(e))
            return None

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.var_views.set(str(data.get("views","")))
            self.var_likes.set(str(data.get("likes","")))
            self.var_seconds.set(str(data.get("seconds","")))
            self.var_title.set(data.get("title",""))
            self.var_thumb.set(data.get("thumbnail",""))
            self.txt_script.delete("1.0","end")
            self.txt_script.insert("1.0", data.get("script_text",""))
            messagebox.showinfo("불러오기 완료", "JSON을 불러왔습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"불러오기 실패: {e}")

    def save_json(self):
        ref = self._collect_input()
        if not ref: return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ref.__dict__, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("저장 완료", "입력을 JSON으로 저장했습니다.")

    def run_analysis(self):
        ref = self._collect_input()
        if not ref: return
        analysis = analyze_reference(ref)
        self._ideas = generate_ideas(ref, n=10)

        # 분석 텍스트 출력
        out_lines = []
        out_lines.append(f"▶ 러닝타임: {analysis['summary']['runtime']}")
        eng = analysis['summary']['engagement']
        out_lines.append(f"▶ 참여율: {eng['engagement_rate']} ({eng['tier']})")
        pace = analysis['summary']['pacing']
        out_lines.append(f"▶ 발화 속도: {pace['wpm']} wpm ({pace['pacing_comment']})")
        title_a = analysis['summary']['title']
        out_lines.append(f"▶ 제목 키워드: {', '.join(title_a['keywords'])}")
        out_lines.append(f"▶ 제목 구체성 점수: {title_a['specificity_score_0_4']}")
        hook = analysis['summary']['hook']
        out_lines.append(f"▶ 훅 미리보기: {hook['hook_preview']} (신호 {hook['score_5']}/5)")
        thumb = analysis['summary']['thumbnail']
        out_lines.append(f"▶ 썸네일 salience: {thumb['salience_score_0_5']}/5")
        out_lines.append("▶ 강점: " + ("; ".join(analysis['strengths']) if analysis['strengths'] else "-"))
        out_lines.append("▶ 리스크: " + ("; ".join(analysis['risks']) if analysis['risks'] else "-"))
        out_lines.append("▶ 성과 이유: " + "; ".join(analysis['why_it_performed']))

        self.txt_analysis.delete("1.0","end")
        self.txt_analysis.insert("1.0","\n".join(out_lines))

        # 아이디어 테이블 채우기
        for row in self.tree.get_children():
            self.tree.delete(row)
        for i, idea in enumerate(self._ideas):
            self.tree.insert("", "end", iid=str(i),
                             values=(idea["idea_title"], idea["concept"], idea["logline"]))

        messagebox.showinfo("완료", "분석이 완료되었습니다. 아이디어 10개가 생성되었습니다.")

    def apply_selected_idea(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("선택 필요", "아이디어를 한 개 선택해주세요.")
            return
        idx = int(sel)
        self._selected_idea = self._ideas[idx]
        # 스크립트 탭으로 전환
        parent = self.page_script.master  # Notebook
        parent.select(self.page_script)

    def build_script(self):
        if not self._selected_idea:
            messagebox.showwarning("아이디어 없음", "먼저 아이디어를 선택해 주세요. ('분석 & 아이디어' 탭)")
            return
        speaker = self.cbo_speaker.get().strip() or "전문가"
        style = self.cbo_style.get().strip() or "스튜디오 톤"
        ch_text = self.var_chapters.get().strip()
        chapters = [c.strip() for c in ch_text.split(",") if c.strip()]
        if not chapters:
            chapters = auto_outline_from_idea(self._selected_idea["idea_title"])

        script = generate_script(self._selected_idea, speaker, chapters, style)
        self.txt_final.delete("1.0","end")
        self.txt_final.insert("1.0", script)
        messagebox.showinfo("대본 생성", "최종 대본을 생성했습니다. '대본 저장'으로 파일로 저장하세요.")

    def save_script(self):
        text = self.txt_final.get("1.0","end").strip()
        if not text:
            messagebox.showwarning("빈 내용", "저장할 대본이 없습니다.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".md",
                                            filetypes=[("Markdown",".md"),("Text",".txt")])
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        messagebox.showinfo("저장 완료", "대본을 저장했습니다.")

if __name__ == "__main__":
    App().mainloop()
