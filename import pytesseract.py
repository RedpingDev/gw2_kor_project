import pytesseract
from translate import Translator
from PIL import ImageGrab
import pyautogui
import tkinter as tk
from tkinter import messagebox, ttk, font
import threading
import time
import json  # DB 로드 위해
import os
from tkinter import Canvas
import tkinter as tk
from tkinter import ttk

# Tesseract 경로 설정 (설치 경로에 맞게)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 번역기 초기화
translator = Translator(to_lang="ko", from_lang="en")

# 로컬 DB 로드 (GitHub에서 다운로드한 txt를 JSON으로 변환 가정)
DB_FILE = 'gw2_kr_db.json'  # 예: {"english": "korean"} 형식
db = {}
if os.path.exists(DB_FILE):
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        db = json.load(f)

# 색상 테마 설정
COLORS = {
    'bg_primary': '#1a1a1a',      # 다크 배경
    'bg_secondary': '#2d2d2d',    # 보조 배경
    'accent': '#4a9eff',          # 액센트 블루
    'accent_hover': '#5ba8ff',    # 호버 블루
    'text_primary': '#ffffff',    # 주 텍스트
    'text_secondary': '#b3b3b3',  # 보조 텍스트
    'success': '#4caf50',         # 성공 그린
    'warning': '#ff9800',         # 경고 오렌지
    'error': '#f44336'            # 에러 레드
}

# tkinter 창 설정
root = tk.Tk()
root.title("🎮 GW2 Korean Overlay")
root.attributes('-topmost', True)  # 항상 위에
root.geometry('600x400+100+100')
root.configure(bg=COLORS['bg_primary'])
root.attributes('-alpha', 0.9)  # 투명도

# 스타일 설정
style = ttk.Style()
style.theme_use('clam')
style.configure('Modern.TButton', 
                background=COLORS['accent'],
                foreground=COLORS['text_primary'],
                borderwidth=0,
                focuscolor='none',
                padding=(10, 8))
style.map('Modern.TButton',
          background=[('active', COLORS['accent_hover']),
                     ('pressed', COLORS['accent'])])

# 영역 설정 변수
capture_bbox = None  # (x1, y1, x2, y2)
selection_window = None
canvas = None
start_x = start_y = 0
end_x = end_y = 0
is_selecting = False

def set_capture_area():
    global capture_bbox, selection_window, canvas, start_x, start_y, end_x, end_y, is_selecting
    
    messagebox.showinfo("영역 선택", "마우스를 드래그하여 영역을 선택하세요")
    root.withdraw()  # 메인 창 숨기기
    
    # 전체 화면 선택 창 생성
    selection_window = tk.Toplevel()
    selection_window.attributes('-fullscreen', True)
    selection_window.attributes('-alpha', 0.3)  # 반투명
    selection_window.configure(bg='black')
    selection_window.attributes('-topmost', True)
    
    # 캔버스 생성
    canvas = Canvas(selection_window, highlightthickness=0, bg='black')
    canvas.pack(fill='both', expand=True)
    
    # 마우스 이벤트 바인딩
    canvas.bind('<Button-1>', start_selection)
    canvas.bind('<B1-Motion>', update_selection)
    canvas.bind('<ButtonRelease-1>', end_selection)
    
    # ESC 키로 취소
    selection_window.bind('<Escape>', cancel_selection)
    selection_window.focus_set()
    
    is_selecting = False

def start_selection(event):
    global start_x, start_y, is_selecting
    start_x, start_y = event.x, event.y
    is_selecting = True

def update_selection(event):
    global end_x, end_y
    if is_selecting:
        end_x, end_y = event.x, event.y
        # 기존 사각형 삭제
        canvas.delete("selection")
        # 새로운 사각형 그리기
        canvas.create_rectangle(start_x, start_y, end_x, end_y, 
                               outline='red', width=2, tags="selection")
        
        # 크기 정보 표시
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)
        canvas.delete("info")
        canvas.create_text(10, 10, text=f"크기: {width}x{height}", 
                          fill='white', font=('Arial', 12), tags="info", anchor='nw')

def end_selection(event):
    global capture_bbox, is_selecting
    if is_selecting:
        end_x, end_y = event.x, event.y
        capture_bbox = (min(start_x, end_x), min(start_y, end_y), 
                       max(start_x, end_x), max(start_y, end_y))
        
        # 선택 창 닫기
        selection_window.destroy()
        root.deiconify()  # 메인 창 다시 보이기
        
        # 결과 표시
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)
        translation_label.config(text=f'영역 설정 완료: {width}x{height} 픽셀', fg=COLORS['success'])
        update_status()
        is_selecting = False

def cancel_selection(event):
    global is_selecting
    selection_window.destroy()
    root.deiconify()
    translation_label.config(text='영역 설정 취소됨', fg=COLORS['text_secondary'])
    is_selecting = False

# 메인 UI 프레임
main_frame = tk.Frame(root, bg=COLORS['bg_primary'])
main_frame.pack(fill='both', expand=True, padx=20, pady=20)

# 헤더 섹션
header_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
header_frame.pack(fill='x', pady=(0, 20))

title_label = tk.Label(header_frame, 
                      text="🎮 GW2 Korean Overlay", 
                      font=('Arial', 18, 'bold'),
                      fg=COLORS['text_primary'],
                      bg=COLORS['bg_primary'])
title_label.pack()

subtitle_label = tk.Label(header_frame,
                         text="실시간 OCR 번역 오버레이",
                         font=('Arial', 10),
                         fg=COLORS['text_secondary'],
                         bg=COLORS['bg_primary'])
subtitle_label.pack()

# 상태 표시 섹션
status_frame = tk.Frame(main_frame, bg=COLORS['bg_secondary'], relief='flat', bd=1)
status_frame.pack(fill='x', pady=(0, 20), ipady=15)

# 상태 표시기들
status_indicators_frame = tk.Frame(status_frame, bg=COLORS['bg_secondary'])
status_indicators_frame.pack(fill='x', padx=15)

# OCR 상태
ocr_status = tk.Label(status_indicators_frame,
                     text="🔍 OCR: 대기 중",
                     font=('Arial', 10),
                     fg=COLORS['warning'],
                     bg=COLORS['bg_secondary'])
ocr_status.pack(side='left')

# 번역 상태
translation_status = tk.Label(status_indicators_frame,
                            text="🌐 번역: 준비됨",
                            font=('Arial', 10),
                            fg=COLORS['success'],
                            bg=COLORS['bg_secondary'])
translation_status.pack(side='left', padx=(20, 0))

# 영역 상태
area_status = tk.Label(status_indicators_frame,
                     text="📐 영역: 미설정",
                     font=('Arial', 10),
                     fg=COLORS['error'],
                     bg=COLORS['bg_secondary'])
area_status.pack(side='right')

# 번역 결과 섹션
translation_frame = tk.Frame(main_frame, bg=COLORS['bg_secondary'], relief='flat', bd=1)
translation_frame.pack(fill='both', expand=True, pady=(0, 20), ipady=15)

translation_label = tk.Label(translation_frame,
                             text="번역 결과가 여기에 표시됩니다...",
                             font=('Arial', 12),
                             fg=COLORS['text_secondary'],
                             bg=COLORS['bg_secondary'],
                             wraplength=500,
                             justify='center')
translation_label.pack(expand=True, fill='both', padx=15, pady=15)

# 버튼 섹션
button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
button_frame.pack(fill='x')

# 영역 설정 버튼
set_area_button = ttk.Button(button_frame, 
                           text="📐 영역 설정", 
                           command=set_capture_area,
                           style='Modern.TButton')
set_area_button.pack(side='left', padx=(0, 10))

# 설정 버튼
settings_button = ttk.Button(button_frame,
                           text="⚙️ 설정",
                           command=lambda: open_settings(),
                           style='Modern.TButton')
settings_button.pack(side='left', padx=(0, 10))

# 번역 히스토리 버튼
history_button = ttk.Button(button_frame,
                          text="📜 히스토리",
                          command=lambda: open_history(),
                          style='Modern.TButton')
history_button.pack(side='left', padx=(0, 10))

# 시작/중지 버튼
toggle_button = ttk.Button(button_frame,
                         text="▶️ 시작",
                         command=lambda: toggle_translation(),
                         style='Modern.TButton')
toggle_button.pack(side='right')

# 전역 변수들
is_running = False
translation_history = []

# 새로운 기능 함수들
def open_settings():
    settings_window = tk.Toplevel(root)
    settings_window.title("⚙️ 설정")
    settings_window.geometry("400x300")
    settings_window.configure(bg=COLORS['bg_primary'])
    settings_window.attributes('-topmost', True)
    
    # 투명도 설정
    tk.Label(settings_window, text="투명도:", font=('Arial', 12), 
             fg=COLORS['text_primary'], bg=COLORS['bg_primary']).pack(pady=10)
    
    transparency_var = tk.DoubleVar(value=0.9)
    transparency_scale = tk.Scale(settings_window, from_=0.1, to=1.0, resolution=0.1,
                                 orient='horizontal', variable=transparency_var,
                                 bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                                 command=lambda x: root.attributes('-alpha', float(x)))
    transparency_scale.pack(fill='x', padx=20)
    
    # 폰트 크기 설정
    tk.Label(settings_window, text="폰트 크기:", font=('Arial', 12),
             fg=COLORS['text_primary'], bg=COLORS['bg_primary']).pack(pady=(20, 10))
    
    font_size_var = tk.IntVar(value=12)
    font_size_scale = tk.Scale(settings_window, from_=8, to=24, orient='horizontal',
                              variable=font_size_var, bg=COLORS['bg_secondary'],
                              fg=COLORS['text_primary'])
    font_size_scale.pack(fill='x', padx=20)
    
    # 저장 버튼
    save_button = ttk.Button(settings_window, text="💾 저장", style='Modern.TButton')
    save_button.pack(pady=20)

def open_history():
    history_window = tk.Toplevel(root)
    history_window.title("📜 번역 히스토리")
    history_window.geometry("500x400")
    history_window.configure(bg=COLORS['bg_primary'])
    history_window.attributes('-topmost', True)
    
    # 히스토리 리스트박스
    history_listbox = tk.Listbox(history_window, bg=COLORS['bg_secondary'],
                               fg=COLORS['text_primary'], font=('Arial', 10))
    history_listbox.pack(fill='both', expand=True, padx=20, pady=20)
    
    # 히스토리 데이터 로드
    for item in translation_history[-50:]:  # 최근 50개만 표시
        history_listbox.insert(tk.END, f"{item['time']} - {item['original']} → {item['translated']}")

def toggle_translation():
    global is_running
    is_running = not is_running
    if is_running:
        toggle_button.config(text="⏸️ 중지")
        ocr_status.config(text="🔍 OCR: 실행 중", fg=COLORS['success'])
    else:
        toggle_button.config(text="▶️ 시작")
        ocr_status.config(text="🔍 OCR: 대기 중", fg=COLORS['warning'])

def update_status():
    """상태 업데이트 함수"""
    if capture_bbox:
        area_status.config(text="📐 영역: 설정됨", fg=COLORS['success'])
    else:
        area_status.config(text="📐 영역: 미설정", fg=COLORS['error'])

def capture_and_translate():
    global is_running
    while True:
        if not is_running or capture_bbox is None:
            time.sleep(1)
            continue
        try:
            ocr_status.config(text="🔍 OCR: 처리 중...", fg=COLORS['warning'])
            img = ImageGrab.grab(bbox=capture_bbox)
            english_text = pytesseract.image_to_string(img, lang='eng')  # 영어 인식
            english_text = english_text.strip()
            
            if english_text:
                # DB 우선 검색
                translated = db.get(english_text, None)
                if translated is None:
                    translation_status.config(text="🌐 번역: 번역 중...", fg=COLORS['warning'])
                    # 온라인 번역
                    translated = translator.translate(english_text)
                    # DB 업데이트 (옵션)
                    db[english_text] = translated
                    with open(DB_FILE, 'w', encoding='utf-8') as f:
                        json.dump(db, f, ensure_ascii=False)
                
                # 번역 결과 업데이트
                translation_label.config(text=translated, fg=COLORS['text_primary'])
                
                # 히스토리에 추가
                translation_history.append({
                    'time': time.strftime("%H:%M:%S"),
                    'original': english_text,
                    'translated': translated
                })
                
                # 상태 업데이트
                translation_status.config(text="🌐 번역: 완료", fg=COLORS['success'])
                ocr_status.config(text="🔍 OCR: 대기 중", fg=COLORS['success'])
            else:
                translation_label.config(text="텍스트를 찾을 수 없습니다...", fg=COLORS['text_secondary'])
                
        except Exception as e:
            translation_label.config(text=f'에러: {str(e)}', fg=COLORS['error'])
            ocr_status.config(text="🔍 OCR: 오류", fg=COLORS['error'])
            
        time.sleep(0.5)  # 폴링 간격 (CPU 절약)

# 스레드 시작
thread = threading.Thread(target=capture_and_translate, daemon=True)
thread.start()

root.mainloop()