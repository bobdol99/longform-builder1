
# Longform Script Builder — Windows EXE Kit (No Local Python Needed)

이 키트는 **로컬에 Python 설치 없이**도 **Windows용 .exe**를 만들 수 있도록
**GitHub Actions (무료)** 파이프라인을 포함합니다. 버튼 한 번으로 클라우드에서 빌드하고,
결과 `.exe`를 아티팩트로 다운로드하세요.

---

## 🚀 가장 쉬운 방법: GitHub Actions로 EXE 만들기

1. 이 폴더(리포지토리)를 GitHub에 새 Repo로 업로드
   - 이름 예: `longform-builder`
2. `Settings → Actions → General` 에서 워크플로우 실행 허용(기본값이면 OK)
3. 상단의 **Actions** 탭 → `Build Windows EXE (Nuitka Standalone)` 워크플로 선택
4. **Run workflow** 버튼 클릭 (또는 `main` 브랜치로 push 시 자동 실행)
5. 실행 완료 후, 해당 워크플로 Run 페이지 하단 **Artifacts**에서
   **`LongformBuilder-EXE`** 다운로드 → `LongformBuilder.exe` 실행!

- 빌드는 **Nuitka Standalone + Onefile**로 구성되어, 별도 설치 없이 실행 가능한 EXE를 생성합니다.
- GUI는 `app/longform_gui.py`이며, 실행 시 앱 내 탭(입력/분석&아이디어/최종대본)으로 동작합니다.

> 참고: GitHub 계정만 있으면 무료 요금제에서 충분히 빌드 가능합니다.

---

## 🖱️ 실행 방법

- 빌드 결과 `LongformBuilder.exe`를 더블클릭 → GUI 실행
- 인터넷 없이 오프라인 사용 가능

---

## 🧩 필요한 파일 구조

```
LongformBuilder_EXE_Kit/
├─ app/
│  └─ longform_gui.py
├─ builder/
│  └─ pyinstaller_build.bat        # (선택) 로컬 PyInstaller 빌드용
└─ .github/workflows/
   └─ windows-exe.yml              # GitHub Actions (Nuitka) 파이프라인
```

> 이미 `app/longform_gui.py`는 포함되어 있습니다.

---

## 🔧 (선택) 로컬에서 EXE 만들기 (나중에 Python을 설치하는 경우)

1. Python 3.11 설치 + `pip install pyinstaller`
2. `builder/pyinstaller_build.bat` 더블클릭
3. `dist/LongformBuilder/LongformBuilder.exe` 생성

---

## 📝 변경/커스터마이즈

- `app/longform_gui.py` 내부에서:
  - 제목/썸네일/훅/파워워드 규칙 및 아이디어 생성 로직(BASE_ANGLES/DIFF_VAULT) 수정
  - 챕터 템플릿·페르소나 멘트·연출 지시 커스터마이즈
- 필요시 `windows-exe.yml`의 Nuitka 옵션 수정:
  - `--windows-console-mode=disable`: 콘솔 창 숨김
  - `--enable-plugin=tk-inter`: Tkinter GUI 플러그인 활성화
  - `--include-data-dir=app=app`: 리소스 동봉

---

## ❓자주 묻는 질문

**Q. Python 없이 정말 가능해요?**  
A. 네. GitHub Actions에서 클라우드로 빌드하고 `.exe`를 Artifact로 받으면 됩니다.

**Q. 실행 시 보안 경고가 뜨는데요?**  
A. 개인 빌드 EXE는 서명이 없어서 SmartScreen 경고가 나올 수 있습니다. “추가 정보 → 실행”을 눌러 진행하거나, 조직 서명 인증서를 통해 서명하세요.

**Q. EXE 용량이 큰데요?**  
A. Standalone onefile은 Python 런타임 포함이라 수십~수백 MB가 될 수 있습니다. 기능 유지에 필요합니다.

---

행복한 제작 되세요! ✨
