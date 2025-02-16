import os
from PIL import Image, ImageTk, ImageFilter, ImageDraw, ImageStat
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

# Конфигурация путей
INPUT_DIR = 'res'
OUTPUT_DIR = 'levels'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Начальные настройки цветов
COLOR_MAP = {}
GRID_COLS = 13
GRID_ROWS = 13
CELL_SIZE = 32
PART_SIZE = 16
HQ_POSITION = (6, 12)  # Нижняя центральная ячейка

class ImageProcessor:
    def __init__(self):
        self.current_image_index = 1
        self.original_image = None
        self.processed_image = None
        self.image_files = [f"{i:02d}.png" for i in range(1, 36)]
        
    def get_current_image_path(self):
        return os.path.join(INPUT_DIR, self.image_files[self.current_image_index-1])

    def load_image(self):
        if self.current_image_index < 1 or self.current_image_index > 35:
            return None
            
        img = Image.open(self.get_current_image_path()).convert('RGB')
        # Применяем размытие для анализа цветов
        self.original_image = img
        #self.processed_image = img.filter(ImageFilter.BLUR)
        self.processed_image = self.original_image
        return self.processed_image

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

def update_image_display():
    img = processor.load_image()
    if img:
        img = img.resize((416, 416), Image.Resampling.LANCZOS)
        img = create_grid_image(img)
        img_tk = ImageTk.PhotoImage(img)
        panel.config(image=img_tk)
        panel.image = img_tk
        update_status()

def update_status():
    status_label.config(text=f"Текущий уровень: {processor.current_image_index:02d}")

def next_image():
    if processor.current_image_index < 35:
        processor.current_image_index += 1
        update_image_display()

def prev_image():
    if processor.current_image_index > 1:
        processor.current_image_index -= 1
        update_image_display()

def is_hq_area(grid_x, grid_y):
    # Проверяем, находится ли ячейка в области HQ или рядом
    return (abs(grid_x - HQ_POSITION[0]) <= 1 and 
            abs(grid_y - HQ_POSITION[1]) <= 1)

def process_level():
    if not processor.original_image:
        messagebox.showerror("Ошибка", "Изображение не загружено!")
        return
    
    level_data = []
    img = processor.original_image.filter(ImageFilter.BLUR)
    
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
                obj_type = COLOR_MAP.get(color)
                
                if obj_type:
                    level_data.append(f"{grid_x},{grid_y},{part},{obj_type}")
    
    output_path = os.path.join(OUTPUT_DIR, f"{processor.current_image_index:02d}")
    with open(output_path, 'w') as f:
        f.write('\n'.join(level_data))
    messagebox.showinfo("Успех", "Обработка завершена!")

def on_mouse_click(event):
    if not processor.processed_image:
        return
    
    x, y = event.x * 416 // panel.winfo_width(), event.y * 416 // panel.winfo_height()
    block_x = (x // PART_SIZE) * PART_SIZE
    block_y = (y // PART_SIZE) * PART_SIZE
    
    # Получаем средний цвет области 16x16 из размытого изображения
    area = processor.processed_image.crop((
        block_x, block_y, 
        block_x + PART_SIZE, 
        block_y + PART_SIZE
    ))
    color = tuple(int(c) for c in ImageStat.Stat(area).mean)
    
    obj_type = simpledialog.askstring("Назначение цвета", 
                                    f"Цвет: {color}\nВведите тип объекта:")
    if obj_type:
        COLOR_MAP[color] = obj_type
        update_color_table()

def update_color_table():
    for child in color_tree.get_children():
        color_tree.delete(child)
    for color, obj_type in COLOR_MAP.items():
        color_tree.insert('', 'end', values=(
            f"{color[0]:3d}, {color[1]:3d}, {color[2]:3d}", 
            obj_type
        ))

# GUI Setup
root = tk.Tk()
root.title("Анализатор уровней")

# Панель изображения
panel = tk.Label(root)
panel.pack()
panel.bind("<Button-1>", on_mouse_click)

# Панель управления
control_frame = tk.Frame(root)
control_frame.pack(pady=10)

tk.Button(control_frame, text="<<", command=prev_image).pack(side=tk.LEFT, padx=5)
tk.Button(control_frame, text=">>", command=next_image).pack(side=tk.LEFT, padx=5)
tk.Button(control_frame, text="Обработать", command=process_level).pack(side=tk.LEFT, padx=5)

# Статус
status_label = tk.Label(root, text="Текущий уровень: 01")
status_label.pack()

# Таблица цветов
color_tree = ttk.Treeview(root, columns=('Color', 'Object'), show='headings')
color_tree.heading('Color', text='Цвет (R, G, B)')
color_tree.heading('Object', text='Объект')
color_tree.column('Color', width=120)
color_tree.column('Object', width=100)
color_tree.pack(padx=10, pady=10)

# Загрузка первого изображения
update_image_display()

root.mainloop()