import os
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

# Конфигурация путей
INPUT_DIR = 'res'
OUTPUT_DIR = 'levels'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Соответствие цветов объектам (настройте под ваши изображения)
COLOR_MAP = {
    (119, 198, 0): 'forest',    # Лес (зеленый)
    (68, 67, 253): 'water',      # Вода (синий)
    (254, 254, 254): 'concrete',  # Бетон (серый)
    (103, 20, 21): 'brick',       # Кирпич (красный)
    (153, 153, 153): 'ice',       # Лед (светло-серый)
    (101, 103, 105): 'hq'             # Штаб (красный)
}

# Размеры сетки уровня
GRID_COLS = 13
GRID_ROWS = 13
CELL_SIZE = 32
PART_SIZE = 16

# Глобальные переменные
loaded_image_path = None
current_image_index = 0
image_files = []

def process_level(image_path, level_num):
    img = Image.open(image_path).convert('RGB')
    level_data = []
    
    for grid_y in range(GRID_ROWS):
        for grid_x in range(GRID_COLS):
            cell_x = grid_x * CELL_SIZE
            cell_y = grid_y * CELL_SIZE
            
            # Проверяем каждую четверть клетки
            parts = {
                'tl': (cell_x, cell_y),
                'tr': (cell_x + PART_SIZE, cell_y),
                'bl': (cell_x, cell_y + PART_SIZE),
                'br': (cell_x + PART_SIZE, cell_y + PART_SIZE)
            }
            
            for part, (px, py) in parts.items():
                # Получаем цвет центрального пикселя четверти
                cx = px + PART_SIZE // 2
                cy = py + PART_SIZE // 2
                if cx >= img.width or cy >= img.height:
                    continue
                
                color = img.getpixel((cx, cy))
                obj_type = COLOR_MAP.get(color)
                
                if obj_type:
                    if obj_type == 'hq':
                        level_data.append(f"hq,{grid_x},{grid_y}")
                    else:
                        level_data.append(f"{grid_x},{grid_y},{part},{obj_type}")
    
    # Сохраняем файл уровня
    output_path = os.path.join(OUTPUT_DIR, f"{level_num:02d}")
    with open(output_path, 'w') as f:
        f.write('\n'.join(level_data))

def load_image():
    global loaded_image_path, current_image_index, image_files
    if not image_files:
        image_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.png')]
        if not image_files:
            messagebox.showerror("Ошибка", "В папке res нет изображений!")
            return
    if current_image_index >= len(image_files):
        current_image_index = 0
    file_path = os.path.join(INPUT_DIR, image_files[current_image_index])
    if file_path:
        img = Image.open(file_path).convert('RGB')  # Конвертируем в RGB режим
        img = img.resize((416, 416), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(img)
        # Рисуем желтую сетку
        for i in range(GRID_COLS + 1):
            x = i * CELL_SIZE
            draw.line((x, 0, x, 416), fill="yellow", width=1)
        for j in range(GRID_ROWS + 1):
            y = j * CELL_SIZE
            draw.line((0, y, 416, y), fill="yellow", width=1)
        img_tk = ImageTk.PhotoImage(img)
        panel.config(image=img_tk)
        panel.image = img_tk
        loaded_image_path = file_path
        current_image_index += 1

def start_processing():
    if not loaded_image_path:
        messagebox.showerror("Ошибка", "Изображение не загружено!")
        return
    level_num = simpledialog.askinteger("Ввод", "Введите номер уровня:", minvalue=1, maxvalue=99)
    if level_num:
        process_level(loaded_image_path, level_num)
        messagebox.showinfo("Успех", "Обработка завершена!")

def edit_color_map():
    def save_changes():
        new_color_map = {}
        for child in tree.get_children():
            color = tuple(map(int, tree.item(child, 'values')[0].split(',')))
            obj_type = tree.item(child, 'values')[1]
            new_color_map[color] = obj_type
        global COLOR_MAP
        COLOR_MAP = new_color_map
        edit_window.destroy()
        messagebox.showinfo("Успех", "COLOR_MAP обновлен!")

    def add_entry():
        color = color_entry.get()
        obj_type = obj_entry.get()
        if color and obj_type:
            try:
                color_tuple = tuple(map(int, color.split(',')))
                tree.insert('', 'end', values=(f"{color_tuple[0]},{color_tuple[1]},{color_tuple[2]}", obj_type))
                color_entry.delete(0, 'end')
                obj_entry.delete(0, 'end')
            except ValueError:
                messagebox.showerror("Ошибка", "Цвет должен быть в формате R,G,B")

    def delete_entry():
        selected_item = tree.selection()
        if selected_item:
            tree.delete(selected_item)

    edit_window = tk.Toplevel(root)
    edit_window.title("Редактировать COLOR_MAP")

    # Таблица для отображения COLOR_MAP
    tree = ttk.Treeview(edit_window, columns=('Color', 'Object'), show='headings')
    tree.heading('Color', text='Цвет (R,G,B)')
    tree.heading('Object', text='Объект')
    tree.pack(padx=10, pady=10)

    for color, obj_type in COLOR_MAP.items():
        tree.insert('', 'end', values=(f"{color[0]},{color[1]},{color[2]}", obj_type))

    # Поля для добавления новых записей
    tk.Label(edit_window, text="Цвет (R,G,B):").pack()
    color_entry = tk.Entry(edit_window)
    color_entry.pack()

    tk.Label(edit_window, text="Объект:").pack()
    obj_entry = tk.Entry(edit_window)
    obj_entry.pack()

    # Кнопки для добавления и удаления записей
    tk.Button(edit_window, text="Добавить", command=add_entry).pack(pady=5)
    tk.Button(edit_window, text="Удалить выбранное", command=delete_entry).pack(pady=5)

    # Кнопка для сохранения изменений
    tk.Button(edit_window, text="Сохранить изменения", command=save_changes).pack(pady=10)

def on_mouse_click(event):
    if not loaded_image_path:
        return
    x, y = event.x, event.y
    # Определяем, в каком блоке 16x16 находится клик
    block_x = (x // PART_SIZE) * PART_SIZE
    block_y = (y // PART_SIZE) * PART_SIZE
    # Загружаем изображение и получаем цвет центрального пикселя блока
    img = Image.open(loaded_image_path).convert('RGB')
    center_x = block_x + PART_SIZE // 2
    center_y = block_y + PART_SIZE // 2
    if center_x >= img.width or center_y >= img.height:
        return
    color = img.getpixel((center_x, center_y))
    # Добавляем цвет в COLOR_MAP
    obj_type = simpledialog.askstring("Ввод", "Введите тип объекта для цвета (R,G,B):")
    if obj_type:
        COLOR_MAP[color] = obj_type
        update_color_map_table()

def update_color_map_table():
    for child in tree.get_children():
        tree.delete(child)
    for color, obj_type in COLOR_MAP.items():
        tree.insert('', 'end', values=(f"{color[0]},{color[1]},{color[2]}", obj_type))

# Основное окно
root = tk.Tk()
root.title("Утилита для анализа изображений")

# Панель для отображения изображения
panel = tk.Label(root)
panel.pack()

# Привязка события клика мыши
panel.bind("<Button-1>", on_mouse_click)

# Кнопки
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

load_btn = tk.Button(button_frame, text="Загрузить изображение", command=load_image)
load_btn.pack(side=tk.LEFT, padx=5)

edit_color_btn = tk.Button(button_frame, text="Настроить COLOR_MAP", command=edit_color_map)
edit_color_btn.pack(side=tk.LEFT, padx=5)

process_btn = tk.Button(button_frame, text="Начать обработку", command=start_processing)
process_btn.pack(side=tk.LEFT, padx=5)

# Таблица для отображения COLOR_MAP
tree = ttk.Treeview(root, columns=('Color', 'Object'), show='headings')
tree.heading('Color', text='Цвет (R,G,B)')
tree.heading('Object', text='Объект')
tree.pack(padx=10, pady=10)

# Заполняем таблицу начальными значениями
update_color_map_table()

root.mainloop()