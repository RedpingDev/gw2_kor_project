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

# DB 시스템 분리
STATIC_DB_FILE = 'gw2_static_db.json'  # 개발자 제공 정형화된 번역본
USER_DB_FILE = 'gw2_user_db.json'      # 사용자 자동 번역 저장소

# 정적 DB 로드 (개발자 제공 번역본)
static_db = {}
if os.path.exists(STATIC_DB_FILE):
    with open(STATIC_DB_FILE, 'r', encoding='utf-8') as f:
        static_db = json.load(f)

# 통합 사용자 데이터 파일
USER_DATA_FILE = 'gw2_user_data.json'
user_data = {
    'translations': {},  # 번역 데이터
    'stats': {}          # 통계 데이터
}

# 사용자 데이터 로드
if os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
        user_data = json.load(f)

# 기존 파일에서 데이터 마이그레이션
if os.path.exists(USER_DB_FILE):
    with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
        user_data['translations'] = json.load(f)

# 기존 통계 파일이 있다면 마이그레이션
if os.path.exists('gw2_user_stats.json'):
    with open('gw2_user_stats.json', 'r', encoding='utf-8') as f:
        user_data['stats'] = json.load(f)

# 통합 데이터로 변수 설정
user_db = user_data['translations']
user_db_stats = user_data['stats']

# 승인 대기열 시스템 제거 (자동 승인으로 변경)

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

# 수정 모드 관련 버튼들 제거

# 시작/중지 버튼
toggle_button = ttk.Button(button_frame,
                         text="▶️ 시작",
                         command=lambda: toggle_translation(),
                         style='Modern.TButton')
toggle_button.pack(side='right')

# 전역 변수들
is_running = False
translation_history = []
# 수정 모드 관련 변수들 제거
manual_mode = False  # 더미 변수 (사용되지 않음)
current_translation = None  # 더미 변수 (사용되지 않음)
capture_paused = False  # 더미 변수 (사용되지 않음)
manual_save_button = None  # 더미 변수 (사용되지 않음)
edit_translation_button = None  # 더미 변수 (사용되지 않음)
skip_translation_button = None  # 더미 변수 (사용되지 않음)
is_worth_saving = lambda x: False  # 더미 함수 (사용되지 않음)

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
    history_window.title("📜 번역 히스토리 & DB 관리")
    history_window.geometry("700x500")
    history_window.configure(bg=COLORS['bg_primary'])
    history_window.attributes('-topmost', True)
    
    # 탭 생성
    notebook = ttk.Notebook(history_window)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)
    
    # 히스토리 탭
    history_frame = tk.Frame(notebook, bg=COLORS['bg_primary'])
    notebook.add(history_frame, text="📜 번역 히스토리")
    
    history_listbox = tk.Listbox(history_frame, bg=COLORS['bg_secondary'],
                               fg=COLORS['text_primary'], font=('Arial', 10))
    history_listbox.pack(fill='both', expand=True, padx=10, pady=10)
    
    # 히스토리 데이터 로드 (DB 소스 정보 포함)
    for item in translation_history[-50:]:  # 최근 50개만 표시
        source_icon = {"정적 DB": "📚", "사용자 DB": "💾", "온라인 번역": "🌐"}.get(item.get('source', ''), "❓")
        history_listbox.insert(tk.END, f"{source_icon} {item['time']} - {item['original']} → {item['translated']}")
    
    # 사용자 DB 관리 탭
    db_frame = tk.Frame(notebook, bg=COLORS['bg_primary'])
    notebook.add(db_frame, text="💾 사용자 DB 관리")
    
    # DB 통계 표시
    stats_text = tk.Text(db_frame, bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], 
                        font=('Arial', 10), wrap='word')
    stats_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    # 통계 정보 생성
    stats_info = f"📊 사용자 DB 통계\n\n"
    stats_info += f"총 저장된 번역: {len(user_db)}개\n"
    stats_info += f"통계 데이터: {len(user_db_stats)}개\n\n"
    
    # 상위 10개 자주 사용된 번역
    if user_db_stats:
        sorted_stats = sorted(user_db_stats.items(), 
                            key=lambda x: x[1].get('frequency', 0), reverse=True)
        stats_info += "🔥 자주 사용된 번역 (상위 10개):\n"
        for i, (text, stats) in enumerate(sorted_stats[:10]):
            freq = stats.get('frequency', 0)
            quality = stats.get('quality_score', 0)
            stats_info += f"{i+1}. {text} (사용: {freq}회, 품질: {quality:.1f}점)\n"
    
    stats_text.insert('1.0', stats_info)
    stats_text.config(state='disabled')
    
    # DB 관리 버튼들
    button_frame = tk.Frame(db_frame, bg=COLORS['bg_primary'])
    button_frame.pack(fill='x', padx=10, pady=5)
    
    clear_db_button = ttk.Button(button_frame, text="🗑️ 사용자 DB 초기화", 
                               command=lambda: clear_user_db())
    clear_db_button.pack(side='left', padx=5)
    
    export_db_button = ttk.Button(button_frame, text="📤 DB 내보내기", 
                                command=lambda: export_user_db())
    export_db_button.pack(side='left', padx=5)

# 승인 대기열 관련 함수들 제거

def clear_user_db():
    """사용자 DB 초기화"""
    global user_db, user_db_stats, user_data
    if messagebox.askyesno("확인", "사용자 DB를 초기화하시겠습니까?"):
        user_db = {}
        user_db_stats = {}
        user_data = {
            'translations': {},
            'stats': {}
        }
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("완료", "사용자 DB가 초기화되었습니다.")

def export_user_db():
    """사용자 DB 내보내기"""
    import tkinter.filedialog as fd
    filename = fd.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        title="사용자 DB 내보내기"
    )
    if filename:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("완료", f"사용자 DB가 {filename}에 저장되었습니다.")

# 수정 모드 관련 함수들 제거

def edit_current_translation():
    """현재 번역을 수정할 수 있는 창 열기"""
    global current_translation, capture_paused
    
    # 디버깅 정보
    print(f"DEBUG: edit_current_translation called")
    print(f"DEBUG: current_translation = {current_translation}")
    print(f"DEBUG: manual_mode = {manual_mode}")
    print(f"DEBUG: current_translation type = {type(current_translation)}")
    
    if not current_translation:
        messagebox.showwarning("수정 불가", "수정할 번역이 없습니다.\n\n수정 모드에서 번역이 감지된 후에 수정할 수 있습니다.")
        return
    
    # 수정 모드가 아닌 경우 경고
    if not manual_mode:
        messagebox.showwarning("수정 불가", "수정 모드에서만 번역을 수정할 수 있습니다.\n\n'수정 모드' 버튼을 눌러 수정 모드로 전환하세요.")
        return
    
    # 캡처 일시정지
    capture_paused = True
    
    # 번역 수정 창
    edit_window = tk.Toplevel(root)
    edit_window.title("✏️ 번역 수정")
    edit_window.geometry("500x300")
    edit_window.configure(bg=COLORS['bg_primary'])
    edit_window.attributes('-topmost', True)
    
    # 메인 프레임
    main_frame = tk.Frame(edit_window, bg=COLORS['bg_primary'])
    main_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # 제목
    title_label = tk.Label(main_frame, text="✏️ 번역 수정", 
                          font=('Arial', 14, 'bold'), fg=COLORS['text_primary'], 
                          bg=COLORS['bg_primary'])
    title_label.pack(pady=(0, 15))
    
    # 영어 텍스트 (수정 가능)
    english_frame = tk.Frame(main_frame, bg=COLORS['bg_secondary'], relief='flat', bd=1)
    english_frame.pack(fill='x', pady=(0, 10), ipady=10)
    
    tk.Label(english_frame, text="영어 텍스트:", 
            font=('Arial', 12), fg=COLORS['text_primary'], 
            bg=COLORS['bg_secondary']).pack(anchor='w', padx=10, pady=(5, 0))
    
    english_entry = tk.Entry(english_frame, font=('Arial', 12), 
                           bg=COLORS['bg_primary'], fg=COLORS['text_primary'],
                           insertbackground=COLORS['text_primary'])
    english_entry.pack(fill='x', padx=10, pady=5)
    english_entry.insert(0, current_translation['english'])
    english_entry.select_range(0, tk.END)  # 전체 텍스트 선택
    
    # 한국어 번역 (수정 가능)
    korean_frame = tk.Frame(main_frame, bg=COLORS['bg_secondary'], relief='flat', bd=1)
    korean_frame.pack(fill='x', pady=(0, 15), ipady=10)
    
    tk.Label(korean_frame, text="한국어 번역:", 
            font=('Arial', 12), fg=COLORS['text_primary'], 
            bg=COLORS['bg_secondary']).pack(anchor='w', padx=10, pady=(5, 0))
    
    korean_entry = tk.Entry(korean_frame, font=('Arial', 12), 
                           bg=COLORS['bg_primary'], fg=COLORS['text_primary'],
                           insertbackground=COLORS['text_primary'])
    korean_entry.pack(fill='x', padx=10, pady=5)
    korean_entry.insert(0, current_translation['korean'])
    korean_entry.select_range(0, tk.END)  # 전체 텍스트 선택
    korean_entry.focus()  # 포커스 설정
    
    # 버튼 프레임
    button_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
    button_frame.pack(fill='x')
    
    def save_edited_translation():
        edited_english = english_entry.get().strip()
        edited_korean = korean_entry.get().strip()
        
        if edited_english and edited_korean:
            # 영어와 한국어 모두 수정
            current_translation['english'] = edited_english
            current_translation['korean'] = edited_korean
            
            translation_label.config(text=f"수정 모드: {edited_korean}\n'번역 저장' 버튼을 눌러 저장하세요", 
                                   fg=COLORS['warning'])
            edit_window.destroy()
            capture_paused = False  # 캡처 재개
        else:
            messagebox.showwarning("입력 오류", "영어와 한국어 번역을 모두 입력해주세요.")
    
    def cancel_edit():
        edit_window.destroy()
        capture_paused = False  # 캡처 재개
    
    # 버튼들
    save_edit_button = ttk.Button(button_frame, text="💾 수정 완료", 
                                command=save_edited_translation, style='Modern.TButton')
    save_edit_button.pack(side='left', padx=5)
    
    cancel_edit_button = ttk.Button(button_frame, text="❌ 취소", 
                                  command=cancel_edit, style='Modern.TButton')
    cancel_edit_button.pack(side='left', padx=5)

def skip_current_translation():
    """현재 번역을 건너뛰고 캡처 재개"""
    global capture_paused, current_translation
    
    # 수정 모드가 아닌 경우 경고
    if not manual_mode:
        messagebox.showwarning("건너뛰기 불가", "수정 모드에서만 번역을 건너뛸 수 있습니다.\n\n'수정 모드' 버튼을 눌러 수정 모드로 전환하세요.")
        return
    
    # 캡처 재개
    capture_paused = False
    
    # 버튼들 숨김
    manual_save_button.pack_forget()
    edit_translation_button.pack_forget()
    skip_translation_button.pack_forget()
    
    # 현재 번역 초기화
    current_translation = None
    
    # 상태 메시지 업데이트
    translation_label.config(text="번역을 건너뛰었습니다. 새로운 번역을 기다리는 중...", 
                           fg=COLORS['text_secondary'])
    
    # 상태 업데이트
    translation_status.config(text="🌐 번역: 대기 중", fg=COLORS['text_secondary'])
    ocr_status.config(text="🔍 OCR: 대기 중", fg=COLORS['success'])

def save_current_translation():
    """현재 번역을 수동으로 저장"""
    global current_translation, capture_paused
    
    print(f"DEBUG: save_current_translation called")
    print(f"DEBUG: current_translation = {current_translation}")
    print(f"DEBUG: current_translation type = {type(current_translation)}")
    
    if not current_translation:
        messagebox.showwarning("저장 불가", "저장할 번역이 없습니다.\n\n수정 모드에서 번역이 감지된 후에 저장할 수 있습니다.")
        return
    
    # 수정 모드가 아닌 경우 경고
    if not manual_mode:
        messagebox.showwarning("저장 불가", "수정 모드에서만 번역을 저장할 수 있습니다.\n\n'수정 모드' 버튼을 눌러 수정 모드로 전환하세요.")
        return
    
    if is_worth_saving(current_translation['english']):
        # 사용자 DB에 저장
        user_db[current_translation['english']] = current_translation['korean']
        user_data['translations'] = user_db
        
        # 통계 업데이트
        update_user_db_stats(current_translation['english'], current_translation['korean'])
        user_data['stats'] = user_db_stats
        
        # 통합 파일에 저장
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        
        # 히스토리에 추가
        translation_history.append({
            'time': time.strftime("%H:%M:%S"),
            'original': current_translation['english'],
            'translated': current_translation['korean'],
            'source': '수동 저장'
        })
        
        messagebox.showinfo("저장 완료", f"번역이 저장되었습니다!\n{current_translation['english']} → {current_translation['korean']}")
        
        # 버튼들 비활성화 및 숨김
        manual_save_button.pack_forget()
        edit_translation_button.pack_forget()
        skip_translation_button.pack_forget()
        
        # 현재 번역 초기화
        current_translation = None
        
        # 캡처 재개
        capture_paused = False
    else:
        # 저장할 수 없는 번역인 경우 건너뛰기 옵션 제공
        if current_translation:
            messagebox.showwarning("저장 불가", "저장할 수 없는 번역입니다.\n(너무 짧거나 이미 충분히 사용된 번역)\n\n건너뛰기를 선택하면 새로운 번역을 기다립니다.")
            
            # 건너뛰기 버튼만 표시
            manual_save_button.pack_forget()
            edit_translation_button.pack_forget()
            skip_translation_button.pack(side='left', padx=(0, 10))
            
            # 건너뛰기 안내 메시지
            translation_label.config(text=f"저장 불가: {current_translation['korean']}\n'건너뛰기' 버튼을 눌러 계속하세요", 
                                   fg=COLORS['error'])
        else:
            # current_translation이 None인 경우
            messagebox.showwarning("저장 불가", "저장할 번역이 없습니다.")
            skip_current_translation()

def toggle_translation():
    global is_running
    is_running = not is_running
    if is_running:
        toggle_button.config(text="⏸️ 중지")
        ocr_status.config(text="🔍 OCR: 실행 중", fg=COLORS['success'])
    else:
        toggle_button.config(text="▶️ 시작")
        ocr_status.config(text="🔍 OCR: 대기 중", fg=COLORS['warning'])

# 자동 저장 관련 함수들 제거

def translate_line_by_line(text, user_db, static_db, translator):
    """줄별로 개별 번역 수행"""
    if not text or len(text) < 5:
        return None, None
    
    lines = text.split('\n')
    if len(lines) < 2:  # 최소 2줄 이상만 줄별 번역
        return None, None
    
    translated_lines = []
    found_any = False
    
    for line in lines:
        line = line.strip()
        if not line:
            translated_lines.append('')
            continue
            
        # 정확한 일치 먼저 확인
        if line in static_db:
            translated_lines.append(static_db[line])
            found_any = True
        elif line in user_db:
            translated_lines.append(user_db[line])
            found_any = True
        else:
            # 개별 줄 번역 (영어인지 확인)
            if any(c.isalpha() for c in line) and not any('\uac00' <= c <= '\ud7af' for c in line):
                try:
                    translated_line = translator.translate(line)
                    translated_lines.append(translated_line)
                    found_any = True
                except:
                    translated_lines.append(line)  # 번역 실패시 원문 유지
            else:
                translated_lines.append(line)  # 한글이거나 특수문자면 원문 유지
    
    if found_any:
        return '\n'.join(translated_lines), "줄별 번역"
    
    return None, None

# 자동 저장 관련 함수들 제거

# 승인 대기열 관련 함수들 제거 (자동 승인으로 변경)

def update_user_db_stats(text, translated):
    """사용자 DB 통계 업데이트"""
    if text not in user_db_stats:
        user_db_stats[text] = {
            'frequency': 0,
            'quality_score': 0,
            'first_seen': time.strftime("%Y-%m-%d %H:%M:%S"),
            'last_seen': time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    user_db_stats[text]['frequency'] += 1
    user_db_stats[text]['last_seen'] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 품질 점수 계산 (번역 길이, 한글 비율 등)
    korean_ratio = sum(1 for c in translated if ord('가') <= ord(c) <= ord('힣')) / len(translated)
    quality_score = min(100, len(translated) * korean_ratio * 10)
    user_db_stats[text]['quality_score'] = max(user_db_stats[text]['quality_score'], quality_score)

def update_status():
    """상태 업데이트 함수"""
    if capture_bbox:
        area_status.config(text="📐 영역: 설정됨", fg=COLORS['success'])
    else:
        area_status.config(text="📐 영역: 미설정", fg=COLORS['error'])

def capture_and_translate():
    global is_running, capture_paused
    while True:
        if not is_running or capture_bbox is None:
            time.sleep(1)
            continue
        
        # 수동 모드에서 캡처 일시정지 상태인 경우
        if capture_paused:
            time.sleep(0.5)
            continue
        try:
            ocr_status.config(text="🔍 OCR: 처리 중...", fg=COLORS['warning'])
            img = ImageGrab.grab(bbox=capture_bbox)
            english_text = pytesseract.image_to_string(img, lang='eng')  # 영어 인식
            english_text = english_text.strip()
            
            if english_text:
                # 1단계: 정적 DB 검색 (개발자 제공 번역본)
                translated = static_db.get(english_text, None)
                db_source = "정적 DB"
                
                if translated is None:
                    # 2단계: 사용자 DB 검색 (자동 번역 저장소)
                    translated = user_db.get(english_text, None)
                    db_source = "사용자 DB"
                    
                    if translated is None:
                        # 3단계: 줄별 번역 (개별 줄 번역)
                        translated, db_source = translate_line_by_line(english_text, user_db, static_db, translator)
                        
                        if translated is None:
                            # 4단계: 온라인 번역 (전체 텍스트)
                            translation_status.config(text="🌐 번역: 번역 중...", fg=COLORS['warning'])
                            translated = translator.translate(english_text)
                            db_source = "온라인 번역"
                        
                # 번역 결과 업데이트
                translation_label.config(text=translated, fg=COLORS['text_primary'])
                
                # 히스토리에 추가 (DB 소스 정보 포함)
                translation_history.append({
                    'time': time.strftime("%H:%M:%S"),
                    'original': english_text,
                    'translated': translated,
                    'source': db_source
                })
                
                # 자동 저장 기능 제거
                
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