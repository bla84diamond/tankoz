import os
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

# Конфигурация путей
INPUT_DIR = 'res'
OUTPUT_DIR = 'levels'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Начальные настройки
GRID_COLS = 13
GRID_ROWS = 13
CELL_SIZE = 32
PART_SIZE = 16
HQ_POSITION = (6, 12)  # Нижняя центральная ячейка

class ImageProcessor:
    def __init__(self):
        self.current_image_index = 1
        self.original_image = None
        self.image_files = [f"{i:02d}.png" for i in range(1, 36)]
        self.color_map = {}
        
    def get_current_image_path(self):
        return os.path.join(INPUT_DIR, self.image_files[self.current_image_index-1])

    def load_image(self):
        if self.current_image_index < 1 or self.current_image_index > 35:
            return None
            
        self.original_image = Image.open(self.get_current_image_path()).convert('RGB')
        return self.original_image

processor = ImageProcessor()

def create_grid_image(img):
    draw = ImageDraw.Draw(img)
    # Рисуем желтую сетку
    for i in range(GRID_COLS + 1):
        x = i * CELL_SIZE
        draw.line((x, 0, x, 416), fill="yellow", width=1)
    for j in range(GRID_ROWS + 1):
        y = j * CELL_SIZE
        draw.line((0, y, 416, y), fill="yellow", width=1)
    return img

def update_display():
    img = processor.load_image()
    if img:
        img = img.resize((416, 416), Image.Resampling.LANCZOS)
        img = create_grid_image(img)
        img_tk = ImageTk.PhotoImage(img)
        panel.config(image=img_tk)
        panel.image = img_tk
        update_status()
        update_preview()

def update_status():
    status_label.config(text=f"Текущий уровень: {processor.current_image_index:02d}")

def next_image():
    if processor.current_image_index < 35:
        processor.current_image_index += 1
        update_display()

def prev_image():
    if processor.current_image_index > 1:
        processor.current_image_index -= 1
        update_display()

def is_hq_area(grid_x, grid_y):
    return (abs(grid_x - HQ_POSITION[0]) <= 1 and 
            abs(grid_y - HQ_POSITION[1]) <= 1)

def generate_level_data():
    level_data = []
    stats = {}
    empty_count = 0
    
    img = processor.original_image
    
    for grid_y in range(GRID_ROWS):
        for grid_x in range(GRID_COLS):
            if is_hq_area(grid_x, grid_y):
                continue
                
            cell_x = grid_x * CELL_SIZE
            cell_y = grid_y * CELL_SIZE
            
            parts = {
                'tl': (cell_x, cell_y),
                'tr': (cell_x + PART_SIZE, cell_y),
                'bl': (cell_x, cell_y + PART_SIZE),
                'br': (cell_x + PART_SIZE, cell_y + PART_SIZE)
            }
            
            for part, (px, py) in parts.items():
                cx = px + PART_SIZE // 2
                cy = py + PART_SIZE // 2
                if cx >= img.width or cy >= img.height:
                    continue
                
                color = img.getpixel((cx, cy))
                obj_type = processor.color_map.get(color)
                
                if obj_type:
                    level_data.append(f"{grid_x},{grid_y},{part},{obj_type}")
                    stats[obj_type] = stats.get(obj_type, 0) + 1
                else:
                    empty_count += 1
                    
    return level_data, stats, empty_count

def update_preview():
    preview_text.delete(1.0, tk.END)
    if not processor.original_image:
        return
    
    level_data, stats, empty_count = generate_level_data()
    
    # Выводим данные уровня
    preview_text.insert(tk.END, "\n".join(level_data))
    preview_text.insert(tk.END, "\n\n--- Статистика ---\n")
    
    # Выводим статистику
    for obj_type, count in stats.items():
        preview_text.insert(tk.END, f"{obj_type}: {count}\n")
        
    preview_text.insert(tk.END, f"\nПустых блоков: {empty_count}")

def process_current_level():
    level_data, _, _ = generate_level_data()
    output_path = os.path.join(OUTPUT_DIR, f"{processor.current_image_index:02d}")
    with open(output_path, 'w') as f:
        f.write("\n".join(level_data))
    messagebox.showinfo("Успех", "Обработка завершена!")

def process_all_levels():
    if not messagebox.askyesno("Подтверждение", "Обработать все уровни?"):
        return
    
    original_index = processor.current_image_index
    total_levels = len(processor.image_files)
    
    for idx in range(1, total_levels+1):
        processor.current_image_index = idx
        processor.load_image()
        level_data, _, _ = generate_level_data()
        output_path = os.path.join(OUTPUT_DIR, f"{idx:02d}")
        with open(output_path, 'w') as f:
            f.write("\n".join(level_data))
        
    processor.current_image_index = original_index
    update_display()
    messagebox.showinfo("Успех", f"Обработано {total_levels} уровней!")

def on_mouse_click(event):
    if not processor.original_image:
        return
    
    x = event.x * 416 // panel.winfo_width()
    y = event.y * 416 // panel.winfo_height()
    
    # Получаем точный цвет пикселя
    color = processor.original_image.getpixel((x, y))
    
    obj_type = simpledialog.askstring("Назначение цвета", 
                                    f"Цвет: {color}\nВведите тип объекта:")
    if obj_type:
        processor.color_map[color] = obj_type
        update_preview()
        update_color_table()

def update_color_table():
    for child in color_tree.get_children():
        color_tree.delete(child)
    for color, obj_type in processor.color_map.items():
        color_tree.insert('', 'end', values=(
            f"{color[0]:3d}, {color[1]:3d}, {color[2]:3d}", 
            obj_type
        ))

# GUI Setup
root = tk.Tk()
root.title("Анализатор уровней")

# Основной фрейм
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

# Панель изображения
img_frame = tk.Frame(main_frame)
img_frame.pack(side=tk.LEFT, padx=10, pady=10)

panel = tk.Label(img_frame)
panel.pack()
panel.bind("<Button-1>", on_mouse_click)

# Панель управления
control_frame = tk.Frame(img_frame)
control_frame.pack(pady=10)

tk.Button(control_frame, text="<<", command=prev_image).pack(side=tk.LEFT, padx=5)
tk.Button(control_frame, text=">>", command=next_image).pack(side=tk.LEFT, padx=5)
tk.Button(control_frame, text="Обработать", command=process_current_level).pack(side=tk.LEFT, padx=5)

# Панель предпросмотра
preview_frame = tk.Frame(main_frame)
preview_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

tk.Label(preview_frame, text="Предпросмотр уровня:").pack(anchor=tk.W)
preview_text = ScrolledText(preview_frame, width=40, height=25)
preview_text.pack(fill=tk.BOTH, expand=True)

# Статус
status_label = tk.Label(root, text="Текущий уровень: 01")
status_label.pack()

# Таблица цветов
color_tree = ttk.Treeview(preview_frame, columns=('Color', 'Object'), show='headings', height=10)
color_tree.heading('Color', text='Цвет (R, G, B)')
color_tree.heading('Object', text='Объект')
color_tree.column('Color', width=120)
color_tree.column('Object', width=100)
color_tree.pack(pady=10, fill=tk.X)

# Кнопка обработки всех уровней
tk.Button(root, text="Обработать все уровни", command=process_all_levels).pack(pady=5)

# Загрузка первого изображения
update_display()

root.mainloop()