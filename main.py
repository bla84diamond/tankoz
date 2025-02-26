import pygame
import sys
import random
from heapq import heappush, heappop

pygame.init()
pygame.joystick.init()
joystick = None
joystick_type = "default"
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    joystick_name = joystick.get_name()
    print(f"Joystick initialized: {joystick_name}")
    if "Dual" in joystick_name or "PS4" in joystick_name:
        joystick_type = "playstation"
    elif "Nintendo" in joystick_name:
        joystick_type = "nintendo"

# Маппинг кнопок для различных типов джойстиков
button_mapping = {
    "default": {
        "A": 1,
        "B": 0,
        "left": 13,
        "right": 14,
        "up": 11,
        "down": 12,
        "start": 7,
        "back": 6,
        "hat_up": (0, 1),
        "hat_down": (0, -1),
        "hat_left": (-1, 0),
        "hat_right": (1, 0)
    },
    "playstation": {
        "A": 1,
        "B": 0,
        "left": 13,
        "right": 14,
        "up": 11,
        "down": 12,
        "start": 6,
        "back": 4,
        "hat_up": (0, 1),
        "hat_down": (0, -1),
        "hat_left": (-1, 0),
        "hat_right": (1, 0)
    },
    "nintendo": {
        "A": 0,
        "B": 1,
        "left": 13,
        "right": 14,
        "up": 11,
        "down": 12,
        "start": 6,
        "back": 4,
        "hat_up": (0, 1),
        "hat_down": (0, -1),
        "hat_left": (-1, 0),
        "hat_right": (1, 0)
    }
}

# =========================
# Параметры отладки
# =========================
show_grid = False        # Видимость сетки
show_masks = False       # Добавлено для отображения масок
show_paths = False  # Переключатель отображения пути для танков врагов

# =========================
# Глобальные переменные
# =========================
### Глобальная переменная для уровня прокачки игрока (1..4)
player_upgrade_level = 1
global_score = 0  # Добавлено для хранения очков
bonus_active = False  # Флаг активного бонуса
bonus_pos = (0, 0)  # Позиция бонуса
bonus_blink = False  # Состояние мерцания бонуса
last_bonus_blink = 0  # Время последнего мерцания
enemy_counter = 1  # Счетчик появившихся врагов
# Глобальные переменные для бонусов и эффекта остановки времени
enemy_stop = False
enemy_stop_end_time = 0
score_life_20000_awarded = False
score_life_100000_awarded = False
# Глобальные переменные для "ежесекундной" вибрации
time_stop_rumble_next = 0    # время (pygame.time.get_ticks()), когда в следующий раз "пульс"
armor_rumble_next = 0        # то же для бонуса "armor"

# =========================
# Глобальные переменные уровня
# =========================
selecting = False
current_level = 1
enemies_to_spawn = 20  # сколько ещё врагов предстоит появиться (из 20)
enemies_remaining_level = 20  # сколько врагов осталось убить в этом уровне
player_lives = 3
game_over = False
game_over_phase = 0  # 0 - движение спрайта, 1 - ожидание, 2 - переход в меню
game_over_sprite = None
last_explosion_times = {} # для отслеживания времени последнего взрыва

# =========================
# Глобальные переменные для HQ Boost
# =========================
hq_boost_active = False
hq_boost_end_time = 0
hq_original_walls = []
hq_temp_walls = pygame.sprite.Group()
blink_state = False
last_blink = 0

# =========================
# Константы размеров
# =========================
CELL_SIZE = 32
GRID_COLS = 13
GRID_ROWS = 13
PLAYABLE_WIDTH = GRID_COLS * CELL_SIZE   # 416
PLAYABLE_HEIGHT = GRID_ROWS * CELL_SIZE    # 416

# Отступы: слева 64, сверху 32, снизу 32 пикселей
LEFT_MARGIN = 64
RIGHT_MARGIN = 64
TOP_MARGIN = 32
BOTTOM_MARGIN = 32

# Игровая поверхность (480x480)
GAME_WIDTH = LEFT_MARGIN + PLAYABLE_WIDTH + RIGHT_MARGIN      # 480
GAME_HEIGHT = TOP_MARGIN + PLAYABLE_HEIGHT + BOTTOM_MARGIN  # 480

# Игровая зона (там движутся танки и пули)
FIELD_RECT = pygame.Rect(LEFT_MARGIN, TOP_MARGIN, PLAYABLE_WIDTH, PLAYABLE_HEIGHT)

# Размер окна
WINDOW_WIDTH = GAME_WIDTH 
WINDOW_HEIGHT = GAME_HEIGHT  # 480

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Battle City PC")

# Поверхности для игры и отладки
game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))

# Загрузка шрифтов
header_font = pygame.font.SysFont("consolas", 16, bold=True)

# Загрузка спрайтов
spritesheet = pygame.image.load("res/sprites.png").convert_alpha()

# Функция вибрации на джойстике
def do_rumble(low, high, duration_ms):
    """Вызывает вибрацию на геймпаде, если он есть, иначе ничего не делает."""
    if joystick is not None and enemies_remaining_level > 0:
        try:
            joystick.rumble(low, high, duration_ms)
        except NotImplementedError:
            # Если вибрация не поддерживается или метод отсутствует
            pass
        except Exception as e:
            print("Rumble error:", e)

def get_sprite(x, y, width, height):
    sprite = pygame.Surface((width, height), pygame.SRCALPHA)
    sprite.blit(spritesheet, (0, 0), (x, y, width, height))
    return sprite

# Определение бонусов с их типами, спрайтами (размер 32x32) и весами (для случайного выбора)
bonus_definitions = [
    {"type": "armor",      "sprite": get_sprite(512, 222, 32, 32), "weight": 30},  # Высокая вероятность
    {"type": "time_stop",  "sprite": get_sprite(544, 222, 32, 32), "weight": 30},  # Высокая вероятность
    {"type": "hq_boost",   "sprite": get_sprite(576, 222, 32, 32), "weight": 20},  # Средняя вероятность
    {"type": "tank_boost", "sprite": get_sprite(608, 222, 32, 32), "weight": 20},  # Средняя вероятность
    {"type": "grenade",    "sprite": get_sprite(640, 222, 32, 32), "weight": 20},  # Средняя вероятность
    {"type": "life",       "sprite": get_sprite(672, 222, 32, 32), "weight": 10}   # Низкая вероятность
]

# Спрайты для цифр (добавлено)
number_sprites = {
    0: get_sprite(657, 367, 16, 16),
    1: get_sprite(673, 367, 16, 16),
    2: get_sprite(689, 367, 16, 16),
    3: get_sprite(705, 367, 16, 16),
    4: get_sprite(721, 367, 16, 16),
    5: get_sprite(657, 383, 16, 16),
    6: get_sprite(673, 383, 16, 16),
    7: get_sprite(689, 383, 16, 16),
    8: get_sprite(705, 383, 16, 16),
    9: get_sprite(721, 383, 16, 16)
}

stage_text_sprite = get_sprite(656, 352, 80, 14)  # Спрайт "STAGE"
level_icon_sprite = get_sprite(752, 368, 32, 32)  # Спрайт иконки уровня

# Функция для рендеринга цифр уровня
def render_level_number(level):
    # Если уровень однозначный, возвращаем 1 спрайт
    if level < 10:
        return [number_sprites[level]]
    else:
        digits = [int(d) for d in str(level)]
        return [number_sprites[d] for d in digits]

# Преобразует число в список спрайтов его цифр.
def render_number(number):
    if number < 0:
        return []
    digits = []
    if number == 0:
        digits.append(0)
    else:
        while number > 0:
            digits.append(number % 10)
            number = number // 10
    digits.reverse()
    return [number_sprites[d] for d in digits]

# Спрайты для танков игрока
# УРОВЕНЬ 1 (как ваш прежний player_sprites)
player_sprites_level1 = {
    "up": [
        get_sprite(0, 0, 32, 32),
        get_sprite(32, 0, 32, 32)
    ],
    "left": [
        get_sprite(64, 0, 32, 32),
        get_sprite(96, 0, 32, 32)
    ],
    "down": [
        get_sprite(128, 0, 32, 32),
        get_sprite(160, 0, 32, 32)
    ],
    "right": [
        get_sprite(192, 0, 32, 32),
        get_sprite(224, 0, 32, 32)
    ]
}

# УРОВЕНЬ 2 (кадры на 32 пикселя ниже по Y, например, 0+32=32, 32+32=64, и т.д.)
player_sprites_level2 = {
    "up": [
        get_sprite(0, 32, 32, 32),
        get_sprite(32, 32, 32, 32)
    ],
    "left": [
        get_sprite(64, 32, 32, 32),
        get_sprite(96, 32, 32, 32)
    ],
    "down": [
        get_sprite(128, 32, 32, 32),
        get_sprite(160, 32, 32, 32)
    ],
    "right": [
        get_sprite(192, 32, 32, 32),
        get_sprite(224, 32, 32, 32)
    ]
}

# УРОВЕНЬ 3 (сдвиг на 64 пикселя по Y)
player_sprites_level3 = {
    "up": [
        get_sprite(0, 64, 32, 32),
        get_sprite(32, 64, 32, 32)
    ],
    "left": [
        get_sprite(64, 64, 32, 32),
        get_sprite(96, 64, 32, 32)
    ],
    "down": [
        get_sprite(128, 64, 32, 32),
        get_sprite(160, 64, 32, 32)
    ],
    "right": [
        get_sprite(192, 64, 32, 32),
        get_sprite(224, 64, 32, 32)
    ]
}

# УРОВЕНЬ 4 (сдвиг на 96 пикселей по Y)
player_sprites_level4 = {
    "up": [
        get_sprite(0, 96, 32, 32),
        get_sprite(32, 96, 32, 32)
    ],
    "left": [
        get_sprite(64, 96, 32, 32),
        get_sprite(96, 96, 32, 32)
    ],
    "down": [
        get_sprite(128, 96, 32, 32),
        get_sprite(160, 96, 32, 32)
    ],
    "right": [
        get_sprite(192, 96, 32, 32),
        get_sprite(224, 96, 32, 32)
    ]
}

enemy_sprites = {
    1: {  # Обычный танк
        "up": [get_sprite(256, 128, 32, 32), get_sprite(288, 128, 32, 32)],
        "left": [get_sprite(320, 128, 32, 32), get_sprite(352, 128, 32, 32)],
        "down": [get_sprite(384, 128, 32, 32), get_sprite(416, 128, 32, 32)],
        "right": [get_sprite(448, 128, 32, 32), get_sprite(480, 128, 32, 32)]
    },
    2: {  # Бронетранспортер
        "up": [get_sprite(256, 160, 32, 32), get_sprite(288, 160, 32, 32)],
        "left": [get_sprite(320, 160, 32, 32), get_sprite(352, 160, 32, 32)],
        "down": [get_sprite(384, 160, 32, 32), get_sprite(416, 160, 32, 32)],
        "right": [get_sprite(448, 160, 32, 32), get_sprite(480, 160, 32, 32)]
    },
    3: {  # Скорострельный танк
        "up": [get_sprite(256, 192, 32, 32), get_sprite(288, 192, 32, 32)],
        "left": [get_sprite(320, 192, 32, 32), get_sprite(352, 192, 32, 32)],
        "down": [get_sprite(384, 192, 32, 32), get_sprite(416, 192, 32, 32)],
        "right": [get_sprite(448, 192, 32, 32), get_sprite(480, 192, 32, 32)]
    },
    4: {  # Тяжелый бронированный танк
        "up": [get_sprite(256, 224, 32, 32), get_sprite(288, 224, 32, 32)],
        "left": [get_sprite(320, 224, 32, 32), get_sprite(352, 224, 32, 32)],
        "down": [get_sprite(384, 224, 32, 32), get_sprite(416, 224, 32, 32)],
        "right": [get_sprite(448, 224, 32, 32), get_sprite(480, 224, 32, 32)]
    }
}

heavy_tank_base_sprites = {
    "up":    [get_sprite(256, 224, 32, 32), get_sprite(288, 224, 32, 32)],
    "left":  [get_sprite(320, 224, 32, 32), get_sprite(352, 224, 32, 32)],
    "down":  [get_sprite(384, 224, 32, 32), get_sprite(416, 224, 32, 32)],
    "right": [get_sprite(448, 224, 32, 32), get_sprite(480, 224, 32, 32)]
}

bonus_enemy_sprites = {
    1: {
        "up": [get_sprite(256, 128+256, 32, 32), get_sprite(288, 128+256, 32, 32)],
        "left": [get_sprite(320, 128+256, 32, 32), get_sprite(352, 128+256, 32, 32)],
        "down": [get_sprite(384, 128+256, 32, 32), get_sprite(416, 128+256, 32, 32)],
        "right": [get_sprite(448, 128+256, 32, 32), get_sprite(480, 128+256, 32, 32)]
    },
    2: {
        "up": [get_sprite(256, 160+256, 32, 32), get_sprite(288, 160+256, 32, 32)],
        "left": [get_sprite(320, 160+256, 32, 32), get_sprite(352, 160+256, 32, 32)],
        "down": [get_sprite(384, 160+256, 32, 32), get_sprite(416, 160+256, 32, 32)],
        "right": [get_sprite(448, 160+256, 32, 32), get_sprite(480, 160+256, 32, 32)]
    },
    3: {
        "up": [get_sprite(256, 192+256, 32, 32), get_sprite(288, 192+256, 32, 32)],
        "left": [get_sprite(320, 192+256, 32, 32), get_sprite(352, 192+256, 32, 32)],
        "down": [get_sprite(384, 192+256, 32, 32), get_sprite(416, 192+256, 32, 32)],
        "right": [get_sprite(448, 192+256, 32, 32), get_sprite(480, 192+256, 32, 32)]
    },
    4: {
        "up": [get_sprite(256, 224+256, 32, 32), get_sprite(288, 224+256, 32, 32)],
        "left": [get_sprite(320, 224+256, 32, 32), get_sprite(352, 224+256, 32, 32)],
        "down": [get_sprite(384, 224+256, 32, 32), get_sprite(416, 224+256, 32, 32)],
        "right": [get_sprite(448, 224+256, 32, 32), get_sprite(480, 224+256, 32, 32)]
    }
}

ARMOR_COLORS = {
    3: [
        (50, 100, 50),    # 1) Темно-зеленый  (health=4)
        (200, 200, 100),  # 2) Желтый         (health=3)
        (100, 200, 100),  # 3) Светло-зеленый (health=2)
        (255, 255, 255)   # 4) Обычный (белый) (health=1)
    ],
    2: [
        (200, 200, 100),  # Желтый         (health=3)
        (100, 200, 100),  # Светло-зеленый (health=2)
        (255, 255, 255)   # Обычный        (health=1)
    ],
    1: [
        (100, 200, 100),  # Светло-зеленый (health=2)
        (255, 255, 255)   # Обычный        (health=1)
    ]
}

bullet_sprites = {
    "up": get_sprite(645, 204, 8, 8),
    "left": get_sprite(660, 203, 8, 8),
    "down": get_sprite(677, 204, 8, 8),
    "right": get_sprite(692, 203, 8, 8)
}

life_icon_sprite = get_sprite(753, 272, 32, 32)  # Иконка танка для жизней

# Спрайт для режима паузы (578,352) 78x14
pause_sprite = get_sprite(578, 352, 78, 14)
# Спрайты защитного поля (анимация, 32x32)
shield_sprites = [
    get_sprite(512, 288, 32, 32),
    get_sprite(544, 288, 32, 32)
]

# Спрайты для отображения очков (32x16)
score_points_sprites = {
    100: get_sprite(576, 327, 32, 16),
    200: get_sprite(608, 327, 32, 16),
    300: get_sprite(640, 327, 32, 16),
    400: get_sprite(672, 327, 32, 16),
    500: get_sprite(704, 327, 32, 16),
}

# Для сетки оставшихся врагов (ячейки 16x16)
present_sprite = get_sprite(640, 384, 16, 16)
absent_sprite = get_sprite(736, 400, 16, 16)
# Вычисляем позиции ячеек относительно боковой панели:
# Начало в общем окне: (496,48); боковая панель начинается с x=480,
# значит относительно боковой панели начальная точка = (16,48)
grid_cells = []
start_grid_x = 16
start_grid_y = 48
# Заполняем ячейки в порядке: по строкам снизу вверх, для каждой строки: сначала правый столбец (col1), затем левый (col0)
for row in reversed(range(10)):  # rows 9..0
    grid_cells.append((start_grid_x + 1*16, start_grid_y + row*16))  # правый столбец
    grid_cells.append((start_grid_x + 0*16, start_grid_y + row*16))  # левый столбец
# Глобальный список статусов ячеек: True = танк ещё не появился (ячейка заполнена)
grid_status = [True] * 20

# =========================
# Звуки
# =========================
player_sound_channel = pygame.mixer.Channel(0)
stand_sound = pygame.mixer.Sound("sounds/stand.ogg")
drive_sound = pygame.mixer.Sound("sounds/drive.ogg")
kill_sound = pygame.mixer.Sound("sounds/kill.ogg")
death_sound = pygame.mixer.Sound("sounds/death.ogg")
shoot_sound = pygame.mixer.Sound("sounds/shoot.ogg")
pause_sound = pygame.mixer.Sound("sounds/pause.ogg")
start_sound = pygame.mixer.Sound("sounds/start.ogg")
wall_sound = pygame.mixer.Sound("sounds/wall.ogg")
minus_armor_sound = pygame.mixer.Sound("sounds/minus_armor.ogg")
bonus_appear_sound = pygame.mixer.Sound("sounds/bonus_appears.ogg")
bonus_take_sound = pygame.mixer.Sound("sounds/bonus_take.ogg")
bonus_life_sound = pygame.mixer.Sound("sounds/bonus_life.ogg")
destroy_sound = pygame.mixer.Sound("sounds/destroy_wall.ogg")
ice_sound = pygame.mixer.Sound("sounds/ice.ogg")
bonus_channel = pygame.mixer.Channel(1)  # Отдельный канал для бонусов
current_player_sound = None  # звук "stand" не запускается, пока игрок не двигается

# Точка появления игрока: 5-я клетка снизу (x=208, y=432)
player_spawn_point = (208, 432)

# Позиции появления врагов (на верхней строке)
spawn_positions = [
    (LEFT_MARGIN + 0 * CELL_SIZE + 16, TOP_MARGIN + 0 * CELL_SIZE + 16),
    (LEFT_MARGIN + 6 * CELL_SIZE + 16, TOP_MARGIN + 0 * CELL_SIZE + 16),
    (LEFT_MARGIN + 12 * CELL_SIZE + 16, TOP_MARGIN + 0 * CELL_SIZE + 16)
]

# =========================
# Группы игровых объектов
# =========================
all_sprites = pygame.sprite.Group()
tank_group = pygame.sprite.Group()     # танки (игрок и враги)
enemies = pygame.sprite.Group()
spawn_group = pygame.sprite.Group()      # анимация появления (препятствие)
explosions = pygame.sprite.Group()       # анимация взрыва
player_bullets = pygame.sprite.Group()   # пули игрока
enemy_bullets = pygame.sprite.Group()    # пули врагов
bonus_group = pygame.sprite.Group()
popups = pygame.sprite.Group()
obstacles = pygame.sprite.Group()
forests = pygame.sprite.Group()          # Группа леса

# =========================
# Класс кирпичной стены (блок)
# =========================
class BrickWall(pygame.sprite.Sprite):
    def __init__(self, x, y, active_cells=("tl", "tr", "bl", "br")):
        super().__init__()
        self.active_cells = set(active_cells)
        self.rect = pygame.Rect(x, y, 32, 32)
        self.base_x = 512
        self.base_y = 128
        self.cells = {}
        for key in ("tl", "tr", "bl", "br"):
            if key in self.active_cells:
                self.cells[key] = {"damage": 0, "side": None}
        self.image = self.build_image()
        self.mask = self.create_mask()

    
    def build_image(self):
        wall_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        positions = {"tl": (0, 0), "tr": (16, 0), "bl": (0, 16), "br": (16, 16)}
        base_sprite = get_sprite(self.base_x, self.base_y, 16, 16)
        for key, pos in positions.items():
            if key not in self.active_cells:
                continue
            cell = self.cells[key]
            if cell["damage"] >= 16:
                continue
            cell_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            if cell["damage"] == 0 or cell["side"] is None:
                cell_surf.blit(base_sprite, (0, 0))
            else:
                d = cell["damage"]
                side = cell["side"]
                if side == "left":
                    remaining = base_sprite.subsurface((d, 0, 16 - d, 16))
                    cell_surf.blit(remaining, (d, 0))
                elif side == "right":
                    remaining = base_sprite.subsurface((0, 0, 16 - d, 16))
                    cell_surf.blit(remaining, (0, 0))
                elif side == "top":
                    remaining = base_sprite.subsurface((0, d, 16, 16 - d))
                    cell_surf.blit(remaining, (0, d))
                elif side == "bottom":
                    remaining = base_sprite.subsurface((0, 0, 16, 16 - d))
                    cell_surf.blit(remaining, (0, 0))
                else:
                    cell_surf.blit(base_sprite, (0, 0))
            wall_surf.blit(cell_surf, pos)
        return wall_surf

    def create_mask(self):
        mask = pygame.mask.from_surface(self.image)
        smaller_mask = pygame.mask.Mask((mask.get_size()[0] - 1, mask.get_size()[1] - 1))
        for y in range(smaller_mask.get_size()[1]):
            for x in range(smaller_mask.get_size()[0]):
                if mask.get_at((x, y)):
                    smaller_mask.set_at((x, y), 1)
        return smaller_mask

    def update_image(self):
        self.image = self.build_image()
        self.mask = self.create_mask()
    
    def take_damage(self, bullet):
        local_x = bullet.rect.centerx - self.rect.x
        local_y = bullet.rect.centery - self.rect.y
        threshold = 6
        damage_value = 8
        updated = False
        cells_to_damage = []
        
        # Горизонтальные выстрелы:
        if bullet.direction in ("left", "right"):
            if bullet.direction == "left":
                default_col = "right"
                fallback_col = "left"
                hit_side = "right"
            else:  # bullet.direction == "right"
                default_col = "left"
                fallback_col = "right"
                hit_side = "left"
            if local_y < 16 - threshold:
                rows = ["top"]
            elif local_y > 16 + threshold:
                rows = ["bottom"]
            else:
                rows = ["top", "bottom"]
            for row in rows:
                if default_col == "left":
                    default_key = "tl" if row == "top" else "bl"
                    fallback_key = "tr" if row == "top" else "br"
                else:
                    default_key = "tr" if row == "top" else "br"
                    fallback_key = "tl" if row == "top" else "bl"
                if default_key in self.cells and self.cells[default_key]["damage"] < 16:
                    cells_to_damage.append(default_key)
                elif fallback_key in self.cells and self.cells[fallback_key]["damage"] < 16:
                    cells_to_damage.append(fallback_key)
        
        # Вертикальные выстрелы:
        elif bullet.direction in ("top", "up", "bottom", "down"):
            if bullet.direction in ("top", "up"):
                default_row = "bottom"
                fallback_row = "top"
                hit_side = "bottom"
            else:
                default_row = "top"
                fallback_row = "bottom"
                hit_side = "top"
            if local_x < 16 - threshold:
                cols = ["left"]
            elif local_x > 16 + threshold:
                cols = ["right"]
            else:
                cols = ["left", "right"]
            for col in cols:
                if col == "left":
                    if default_row == "bottom":
                        default_key = "bl"
                        fallback_key = "tl"
                    else:
                        default_key = "tl"
                        fallback_key = "bl"
                else:  # col == "right"
                    if default_row == "bottom":
                        default_key = "br"
                        fallback_key = "tr"
                    else:
                        default_key = "tr"
                        fallback_key = "br"
                if default_key in self.cells and self.cells[default_key]["damage"] < 16:
                    cells_to_damage.append(default_key)
                elif fallback_key in self.cells and self.cells[fallback_key]["damage"] < 16:
                    cells_to_damage.append(fallback_key)
        else:
            return True
        
        cells_to_damage = list(set(cells_to_damage))
        for key in cells_to_damage:
            cell = self.cells[key]
            if cell["damage"] < 16:
                cell["side"] = hit_side
                cell["damage"] = min(cell["damage"] + damage_value, 16)
                updated = True
        
        if updated:
            if bullet.owner == "player":
                destroy_sound.play()
            self.update_image()
        if all(self.cells[k]["damage"] >= 16 for k in self.cells):
            self.kill()
        return True
    
    def collides_with_point(self, point):
        local_x = point[0] - self.rect.x
        local_y = point[1] - self.rect.y
        try:
            return self.mask.get_at((int(local_x), int(local_y))) != 0
        except IndexError:
            return False
    
    def draw(self, surface):
        surface.blit(self.image, self.rect.topleft)

# =========================
# Класс леса (блок из 4 элементов)
# =========================
class Forest(pygame.sprite.Sprite):
    def __init__(self, x, y, active_cells=("tl", "tr", "bl", "br")):
        """
        Блок леса, состоящий из 1, 2, 3 или 4 элементов 16x16.
        По умолчанию создается полный блок (4 элемента) размером 32x32.
        
        Спрайт для одного элемента леса берётся из sprites.png по координатам (528,144).
        Остальные свойства (скрытие танка и т.д.) остаются прежними.
        """
        super().__init__()
        self.active_cells = set(active_cells)
        # Для упрощения размер блока всегда 32x32
        self.rect = pygame.Rect(x, y, 32, 32)
        self.image = self.build_image()
    
    def build_image(self):
        forest_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        positions = {
            "tl": (0, 0),
            "tr": (16, 0),
            "bl": (0, 16),
            "br": (16, 16)
        }
        base_sprite = get_sprite(528, 144, 16, 16)
        for key, pos in positions.items():
            if key in self.active_cells:
                forest_surf.blit(base_sprite, pos)
        return forest_surf

# =========================
# Класс бетонной стены (шаблон)
# =========================
class ConcreteWall(pygame.sprite.Sprite):
    def __init__(self, x, y, active_cells=("tl", "tr", "bl", "br")):
        super().__init__()
        self.active_cells = set(active_cells)
        self.rect = pygame.Rect(x, y, 32, 32)
        self.base_x = 512
        self.base_y = 144
        self.cells = {}
        for key in ("tl", "tr", "bl", "br"):
            if key in self.active_cells:
                self.cells[key] = {"damage": 0, "side": None}
        self.image = self.build_image()
        self.mask = self.create_mask()

    def build_image(self):
        wall_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        positions = {"tl": (0, 0), "tr": (16, 0), "bl": (0, 16), "br": (16, 16)}
        base_sprite = get_sprite(self.base_x, self.base_y, 16, 16)
        for key, pos in positions.items():
            if key not in self.active_cells:
                continue
            cell = self.cells[key]
            if cell["damage"] >= 16:
                continue
            cell_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            if cell["damage"] == 0 or cell["side"] is None:
                cell_surf.blit(base_sprite, (0, 0))
            else:
                d = cell["damage"]
                side = cell["side"]
                if side == "left":
                    remaining = base_sprite.subsurface((d, 0, 16 - d, 16))
                    cell_surf.blit(remaining, (d, 0))
                elif side == "right":
                    remaining = base_sprite.subsurface((0, 0, 16 - d, 16))
                    cell_surf.blit(remaining, (0, 0))
                elif side == "top":
                    remaining = base_sprite.subsurface((0, d, 16, 16 - d))
                    cell_surf.blit(remaining, (0, d))
                elif side == "bottom":
                    remaining = base_sprite.subsurface((0, 0, 16, 16 - d))
                    cell_surf.blit(remaining, (0, 0))
                else:
                    cell_surf.blit(base_sprite, (0, 0))
            wall_surf.blit(cell_surf, pos)
        return wall_surf

    def create_mask(self):
        mask = pygame.mask.from_surface(self.image)
        smaller_mask = pygame.mask.Mask((mask.get_size()[0] - 1, mask.get_size()[1] - 1))
        for y in range(smaller_mask.get_size()[1]):
            for x in range(smaller_mask.get_size()[0]):
                if mask.get_at((x, y)):
                    smaller_mask.set_at((x, y), 1)
        return smaller_mask

    def update_image(self):
        self.image = self.build_image()
        self.mask = self.create_mask()

    def take_damage(self, bullet):
        global player_upgrade_level
        explosion_created = False
        if not (bullet.owner == "player" and player_upgrade_level == 4):
            wall_sound.play()
            if not explosion_created:
                create_hit_explosion(bullet.rect.center)
                explosion_created = True
            return True

        local_x = bullet.rect.centerx - self.rect.x
        local_y = bullet.rect.centery - self.rect.y
        threshold = 6
        damage_value = 16
        updated = False
        cells_to_destroy = []

        if bullet.direction in ("left", "right"):
            if bullet.direction == "left":
                default_col = "right"
                fallback_col = "left"
                hit_side = "right"
            else:
                default_col = "left"
                fallback_col = "right"
                hit_side = "left"
            if local_y < 16 - threshold:
                rows = ["top"]
            elif local_y > 16 + threshold:
                rows = ["bottom"]
            else:
                rows = ["top", "bottom"]
            for row in rows:
                if default_col == "left":
                    default_key = "tl" if row == "top" else "bl"
                    fallback_key = "tr" if row == "top" else "br"
                else:
                    default_key = "tr" if row == "top" else "br"
                    fallback_key = "tl" if row == "top" else "bl"
                if default_key in self.cells and self.cells[default_key]["damage"] < 16:
                    cells_to_destroy.append(default_key)
                elif fallback_key in self.cells and self.cells[fallback_key]["damage"] < 16:
                    cells_to_destroy.append(fallback_key)

        elif bullet.direction in ("top", "up", "bottom", "down"):
            if bullet.direction in ("top", "up"):
                default_row = "bottom"
                fallback_row = "top"
                hit_side = "bottom"
            else:
                default_row = "top"
                fallback_row = "bottom"
                hit_side = "top"
            if local_x < 16 - threshold:
                cols = ["left"]
            elif local_x > 16 + threshold:
                cols = ["right"]
            else:
                cols = ["left", "right"]
            for col in cols:
                if col == "left":
                    if default_row == "bottom":
                        default_key = "bl"
                        fallback_key = "tl"
                    else:
                        default_key = "tl"
                        fallback_key = "bl"
                else:
                    if default_row == "bottom":
                        default_key = "br"
                        fallback_key = "tr"
                    else:
                        default_key = "tr"
                        fallback_key = "br"
                if default_key in self.cells and self.cells[default_key]["damage"] < 16:
                    cells_to_destroy.append(default_key)
                elif fallback_key in self.cells and self.cells[fallback_key]["damage"] < 16:
                    cells_to_destroy.append(fallback_key)
        else:
            return True

        cells_to_destroy = list(set(cells_to_destroy))
        explosion_created = False
        for key in cells_to_destroy:
            if self.cells[key]["damage"] < 16:
                self.cells[key]["damage"] = damage_value
                self.cells[key]["side"] = hit_side
                updated = True
                if not explosion_created:
                    create_hit_explosion(bullet.rect.center)
                    explosion_created = True

        if updated:
            if bullet.owner == "player":
                wall_sound.play()
            self.update_image()
        if all(self.cells[k]["damage"] >= 16 for k in self.cells):
            self.kill()
        return True

# =========================
# Класс водного блока (шаблон)
# =========================
class Water(pygame.sprite.Sprite):
    def __init__(self, x, y, active_cells=("tl", "tr", "bl", "br")):
        super().__init__()
        self.active_cells = set(active_cells)
        self.rect = pygame.Rect(x, y, 32, 32)
        self.base_x = 544
        self.base_y = 160
        self.frames = [
            self.build_image(0),
            self.build_image(16),
            self.build_image(32),
            self.build_image(16)
        ]
        self.current_frame = 0
        self.last_update = pygame.time.get_ticks()
        self.frame_duration = 500  # 500 мс на кадр
        self.image = self.frames[self.current_frame]
        self.mask = self.create_mask()
    
    def build_image(self, offset_x):
        water_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        positions = {"tl": (0, 0), "tr": (16, 0), "bl": (0, 16), "br": (16, 16)}
        base_sprite = get_sprite(self.base_x - offset_x, self.base_y, 16, 16)
        for key, pos in positions.items():
            if key in self.active_cells:
                water_surf.blit(base_sprite, pos)
        return water_surf

    def create_mask(self):
        mask = pygame.mask.from_surface(self.image)
        smaller_mask = pygame.mask.Mask((mask.get_size()[0] - 1, mask.get_size()[1] - 1))
        for y in range(smaller_mask.get_size()[1]):
            for x in range(smaller_mask.get_size()[0]):
                if mask.get_at((x, y)):
                    smaller_mask.set_at((x, y), 1)
        return smaller_mask

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_update > self.frame_duration:
            self.last_update = now
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.image = self.frames[self.current_frame]
            self.mask = self.create_mask()

# =========================
# Класс ледяного блока (шаблон)
# =========================
class Ice(pygame.sprite.Sprite):
    def __init__(self, x, y, active_cells=("tl", "tr", "bl", "br")):
        super().__init__()
        self.active_cells = set(active_cells)
        self.rect = pygame.Rect(x, y, 32, 32)
        self.base_x = 544
        self.base_y = 144
        self.image = self.build_image()
        self.mask = self.create_mask()
    
    def build_image(self):
        ice_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        positions = {"tl": (0, 0), "tr": (16, 0), "bl": (0, 16), "br": (16, 16)}
        base_sprite = get_sprite(self.base_x, self.base_y, 16, 16)
        for key, pos in positions.items():
            if key in self.active_cells:
                ice_surf.blit(base_sprite, pos)
        return ice_surf
    
    def create_mask(self):
        mask = pygame.mask.from_surface(self.image)
        smaller_mask = pygame.mask.Mask((mask.get_size()[0] - 1, mask.get_size()[1] - 1))
        for y in range(smaller_mask.get_size()[1]):
            for x in range(smaller_mask.get_size()[0]):
                if mask.get_at((x, y)):
                    smaller_mask.set_at((x, y), 1)
        return smaller_mask

# =========================
# Класс отображения очков
# =========================
class ScorePopup(pygame.sprite.Sprite):
    def __init__(self, pos, points, duration=500):
        super().__init__()
        self.image = score_points_sprites[points]  # Берёт нужный спрайт из словаря
        self.rect = self.image.get_rect(center=pos)
        self.start_time = pygame.time.get_ticks()
        # duration теперь задаётся извне (по умолчанию 500 мс)
        self.duration = duration

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.start_time > self.duration:
            self.kill()

# =========================
# Класс Bonus
# =========================
class Bonus(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.bonus_data = random.choices(bonus_definitions, weights=[bd["weight"] for bd in bonus_definitions])[0]
        self.type = self.bonus_data["type"]
        self.image = self.bonus_data["sprite"]
        self.rect = self.image.get_rect(center=pos)
        self.mask = pygame.mask.Mask((20, 20), fill=True)
        self.spawn_time = pygame.time.get_ticks()
        all_sprites.add(self)
        bonus_group.add(self)
        bonus_channel.play(bonus_appear_sound)
        self.last_blink_time = self.spawn_time
        self.blink_state = True

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_blink_time >= 250:
            self.blink_state = not self.blink_state
            self.last_blink_time = now
        if self.blink_state:
            self.image.set_alpha(255)
        else:
            self.image.set_alpha(0)

def can_spawn_bonus_at(pos):
    # Проверяем, не находится ли бонус в ячейке с танком игрока
    if player and player.rect.collidepoint(pos):
        return False

    # Проверяем, не находится ли бонус в ячейке спавна врагов
    for spawn_pos in spawn_positions:
        if pygame.Rect(spawn_pos[0] - 16, spawn_pos[1] - 16, 32, 32).collidepoint(pos):
            return False

    # Проверяем, не находится ли бонус в ячейке штаба или ячейках, окружающих штаб
    hq_x, hq_y = LEFT_MARGIN + 6 * CELL_SIZE, TOP_MARGIN + 12 * CELL_SIZE
    hq_rect = pygame.Rect(hq_x - 16, hq_y - 16, 64, 64)
    if hq_rect.collidepoint(pos):
        return False

    return True

def spawn_bonus():
    cols = GRID_COLS - 2
    rows = GRID_ROWS - 2
    while True:
        rand_col = random.randint(1, cols)
        rand_row = random.randint(1, rows)
        bonus_x = LEFT_MARGIN + (rand_col * CELL_SIZE) - CELL_SIZE // 2
        bonus_y = TOP_MARGIN + (rand_row * CELL_SIZE) - CELL_SIZE // 2
        # Добавляем случайное смещение на 16 пикселей
        offset_x = random.choice([-16, 0, 16])
        offset_y = random.choice([-16, 0, 16])
        bonus_x += offset_x
        bonus_y += offset_y
        if can_spawn_bonus_at((bonus_x, bonus_y)):
            Bonus((bonus_x, bonus_y))
            break

# Функция поиска пути
def find_path(start, goal):
    # Улучшенный AI алгоритм с учетом размера танка
    
    start_col = (start[0] - LEFT_MARGIN) // CELL_SIZE
    start_row = (start[1] - TOP_MARGIN) // CELL_SIZE
    goal_col = (goal[0] - LEFT_MARGIN) // CELL_SIZE
    goal_row = (goal[1] - TOP_MARGIN) // CELL_SIZE

    open_set = []
    heappush(open_set, (0, start_col, start_row))
    came_from = {}
    g_score = {(start_col, start_row): 0}
    
    obstacles_grid = build_obstacles_grid(radius=2)  # Учитываем размер танка 2x2 клетки

    while open_set:
        current = heappop(open_set)
        current_col, current_row = current[1], current[2]

        if (current_col, current_row) == (goal_col, goal_row):
            path = []
            while (current_col, current_row) in came_from:
                path.append((
                    LEFT_MARGIN + current_col * CELL_SIZE + CELL_SIZE//2,
                    TOP_MARGIN + current_row * CELL_SIZE + CELL_SIZE//2
                ))
                current_col, current_row = came_from[(current_col, current_row)]
            return path[::-1]

        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
            new_col = current_col + dx
            new_row = current_row + dy
            if 0 <= new_col < GRID_COLS and 0 <= new_row < GRID_ROWS:
                if is_area_clear(new_col, new_row, radius=1):
                    tentative_g = g_score[(current_col, current_row)] + 1
                    if (new_col, new_row) not in g_score or tentative_g < g_score[(new_col, new_row)]:
                        came_from[(new_col, new_row)] = (current_col, current_row)
                        g_score[(new_col, new_row)] = tentative_g
                        f_score = tentative_g + heuristic(new_col, new_row, goal_col, goal_row)
                        heappush(open_set, (f_score, new_col, new_row))

    return []

def heuristic(col, row, goal_col, goal_row):
    return abs(col - goal_col) + abs(row - goal_row)

def is_area_clear(col, row, radius=1):
    obstacles_grid = build_obstacles_grid(radius)
    # Проверяем область 3x3 для проходимости
    for i in range(-radius, radius+1):
        for j in range(-radius, radius+1):
            if 0 <= row + j < GRID_ROWS and 0 <= col + i < GRID_COLS:
                if obstacles_grid[row+j][col+i] != 0:
                    return False
    return True

def build_obstacles_grid(radius=1):
    grid = [[0 for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    for obstacle in obstacles:
        if isinstance(obstacle, (BrickWall, ConcreteWall, Water)):
            col = (obstacle.rect.left - LEFT_MARGIN) // CELL_SIZE
            row = (obstacle.rect.top - TOP_MARGIN) // CELL_SIZE
            for i in range(-radius, radius + 1):
                for j in range(-radius, radius + 1):
                    if 0 <= col + i < GRID_COLS and 0 <= row + j < GRID_ROWS:
                        if obstacle.mask.get_at((col + i, row + j)):
                            grid[row + j][col + i] = 1
    return grid

# Функция проверки попадания в штаб
def check_hq_hit(bullet):
    hq_cell_x = 6  # Фиксированная позиция штаба
    hq_cell_y = 12
    
    # Переводим координаты пули в клеточные координаты
    grid_x = (bullet.rect.centerx - LEFT_MARGIN) // CELL_SIZE
    grid_y = (bullet.rect.centery - TOP_MARGIN) // CELL_SIZE
    
    return grid_x == hq_cell_x and grid_y == hq_cell_y

# =========================
# Класс штаба игрока
# =========================
class Headquarters(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.grid_x = 6
        self.grid_y = 12
        self.normal_sprite = get_sprite(608, 64, 32, 32)
        self.destroyed_sprite = get_sprite(640, 64, 32, 32)
        self.image = self.normal_sprite
        self.rect = self.image.get_rect(
            topleft=(LEFT_MARGIN + self.grid_x * CELL_SIZE,
                     TOP_MARGIN + self.grid_y * CELL_SIZE))
        self.destroyed = False
        self.mask = pygame.mask.from_surface(self.image)  # Инициализация маски

    def destroy(self):
        if self.destroyed:
            return
        self.destroyed = True
        self.image = self.destroyed_sprite
        self.mask = pygame.mask.from_surface(self.image)  # Обновление маски
        explosion = Explosion(self.rect.center)
        explosions.add(explosion)
        all_sprites.add(explosion)
        global game_over
        game_over = True
        start_game_over_sequence()
        pygame.mixer.stop()
        death_sound.play()

# =========================
# Класс для взрыва при попадании
# =========================
class HitExplosion(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.pos = (pos[0] + random.randint(-3, 3), pos[1] + random.randint(-3, 3))
        frame0 = get_sprite(511, 256, 32, 32)
        frame1 = get_sprite(544, 256, 32, 32)
        self.frames = [frame0, frame1]
        self.total_frames = len(self.frames)
        self.frame_duration = 50  # по 50 мс на кадр
        self.start_time = pygame.time.get_ticks()
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=self.pos)
    
    def update(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.start_time
        index = int(elapsed // self.frame_duration)
        if index < self.total_frames:
            self.image = self.frames[index]
        else:
            self.kill()

def create_hit_explosion(pos):
    global last_explosion_times
    current_time = pygame.time.get_ticks()
    if pos in last_explosion_times:
        if current_time - last_explosion_times[pos] < 200:  # 200 мс интервал
            return
    last_explosion_times[pos] = current_time
    explosion = HitExplosion(pos)
    explosions.add(explosion)
    all_sprites.add(explosion)

# =========================
# Класс Explosion – анимация взрыва (5 кадров, 500 мс)
# =========================
class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos, score_points=None, popup_duration=500):
        super().__init__()
        self.pos = pos
        frame0 = get_sprite(511, 256, 32, 32)
        frame1 = get_sprite(544, 256, 32, 32)
        frame2 = get_sprite(576, 256, 32, 32)
        frame3 = get_sprite(608, 256, 64, 64)
        frame4 = get_sprite(672, 256, 64, 64)
        self.frames = [frame0, frame1, frame2, frame3, frame4]
        self.total_frames = len(self.frames)
        self.total_duration = 400  # длительность анимации взрыва
        self.frame_duration = self.total_duration / self.total_frames
        self.start_time = pygame.time.get_ticks()
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=self.pos)

        self.score_points = score_points
        # Новое поле – продолжительность спрайта очков
        self.popup_duration = popup_duration

    def update(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.start_time
        index = int(elapsed // self.frame_duration)
        if index < self.total_frames:
            self.image = self.frames[index]
            self.rect = self.image.get_rect(center=self.pos)
        else:
            self.kill()
            # Если нужно показать очки — создаём всплывающий спрайт
            if self.score_points is not None:
                popup = ScorePopup(self.pos, self.score_points, duration=self.popup_duration)
                popups.add(popup)

# =========================
# Класс SpawnAnimation – анимация появления (для врагов)
# =========================
class SpawnAnimation(pygame.sprite.Sprite):
    def __init__(self, pos, callback):
        super().__init__()
        self.pos = pos
        frame0 = get_sprite(512, 191, 32, 32)
        frame1 = get_sprite(544, 191, 32, 32)
        frame2 = get_sprite(576, 191, 32, 32)
        frame3 = get_sprite(608, 191, 32, 32)
        cycle = [frame0, frame1, frame2, frame3, frame2, frame1, frame0]
        self.frames = cycle * 2
        self.total_frames = len(self.frames)
        self.total_duration = 1000  # мс
        self.frame_duration = self.total_duration / self.total_frames
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=self.pos)
        self.start_time = pygame.time.get_ticks()
        self.callback = callback

    def update(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.start_time
        index = int(elapsed // self.frame_duration)
        if index < self.total_frames:
            self.image = self.frames[index]
        else:
            self.callback(self.rect.center)
            self.kill()

# =========================
# Класс Tank – базовый класс для танков (игрока и врагов)
# =========================
class Tank(pygame.sprite.Sprite):
    def __init__(self, x, y, is_player=True, enemy_type=None, upgrade_level=1):
        super().__init__()
        self.is_player = is_player
        self.shoot_cooldown = 0
        
        if is_player:
            self.sprites = player_sprites_level1
            self.speed = 3
        else:
            self.speed = 2
            if enemy_type is None:
                enemy_type = 1
            self.sprites = {
                direction: [frame.copy() for frame in frames]
                for direction, frames in enemy_sprites[enemy_type].items()
            }

        self.direction = "up"
        self.current_sprite = 0
        self.image = self.sprites[self.direction][self.current_sprite]
        self.rect = self.image.get_rect(center=(x, y))

        # Создаем маску 28x28 пикселей для танка
        self.mask = pygame.mask.Mask((25, 25), fill=True)

        if is_player:
            self.bullet_speed = 5
            self.can_double_shot = False
            self.armor_piercing = False
            self.set_upgrade_level(upgrade_level)
        
        self.last_update = pygame.time.get_ticks()
        self.animation_interval = 25
        self.is_alive = True
        self.is_moving = False
        self.last_key = None
        self.shield_unlimited = False
        self.shots_in_burst = 0
        self.last_shot_time = 0
        
        self.enemy_type = enemy_type
        
        if is_player:
            self.set_upgrade_level(upgrade_level)

    def set_upgrade_level(self, level):
        self.upgrade_level = level
        
        # 1) Выбираем готовый словарь спрайтов
        if level == 1:
            self.sprites = player_sprites_level1
        elif level == 2:
            self.sprites = player_sprites_level2
        elif level == 3:
            self.sprites = player_sprites_level3
        elif level == 4:
            self.sprites = player_sprites_level4

        # 2) Меняем скорость пули и флаги
        if level == 1:
            self.bullet_speed = 5
            self.can_double_shot = False
            self.armor_piercing = False
        elif level == 2:
            self.bullet_speed = 10
            self.can_double_shot = False
            self.armor_piercing = False
        elif level == 3:
            self.bullet_speed = 10
            self.can_double_shot = True
            self.armor_piercing = False
        elif level == 4:
            self.bullet_speed = 10
            self.can_double_shot = True
            self.armor_piercing = True

        # 3) Пересоздаём rect по центру, чтобы обновить self.image
        old_center = self.rect.center
        self.current_sprite = 0
        self.image = self.sprites[self.direction][self.current_sprite]
        self.rect = self.image.get_rect(center=old_center)

    def ai_update(self):
        """Базовый метод для ИИ управления (пустая реализация)"""
        pass

    def update(self, input_keys=None):
        global show_masks
        if game_over:  # Блокируем обновление позиции
            return
        if self.is_alive and self.is_player:
            if input_keys is None:
                return  # Если input_keys не передан, выходим из метода
            old_rect = self.rect.copy()
            old_direction = self.direction  # Сохраняем предыдущее направление для сравнения

            self.is_moving = False

            # Обработка управления
            if input_keys.get(pygame.K_UP) or input_keys.get(pygame.K_w):
                self.last_key = pygame.K_UP
            elif input_keys.get(pygame.K_DOWN) or input_keys.get(pygame.K_s):
                self.last_key = pygame.K_DOWN
            elif input_keys.get(pygame.K_LEFT) or input_keys.get(pygame.K_a):
                self.last_key = pygame.K_LEFT
            elif input_keys.get(pygame.K_RIGHT) or input_keys.get(pygame.K_d):
                self.last_key = pygame.K_RIGHT
            else:
                self.last_key = None

            # Движение и обновление направления
            if self.last_key == pygame.K_UP:
                self.rect.y -= self.speed
                self.direction = "up"
            elif self.last_key == pygame.K_DOWN:
                self.rect.y += self.speed
                self.direction = "down"
            elif self.last_key == pygame.K_LEFT:
                self.rect.x -= self.speed
                self.direction = "left"
            elif self.last_key == pygame.K_RIGHT:
                self.rect.x += self.speed
                self.direction = "right"

            # Ограничиваем движение в пределах игровой зоны
            self.rect.clamp_ip(FIELD_RECT)

            # Проверка столкновения с препятствиями (включая воду, бетон, кирпич и т.д.)
            for obstacle in obstacles:
                # Пропускаем лед – по льду танки могут ездить
                if isinstance(obstacle, Ice):
                    continue
                if hasattr(obstacle, 'mask'):
                    offset = (obstacle.rect.x - self.rect.x, obstacle.rect.y - self.rect.y)
                    if self.mask.overlap(obstacle.mask, offset):
                        self.rect = old_rect
                        break
                else:
                    if self.rect.colliderect(obstacle.rect):
                        self.rect = old_rect
                        break

            # Обработка эффекта льда для игрока:
            # Если танк пересекается с блоком льда, то при смене направления на противоположное
            # воспроизводится звук и танк продолжает инерционное движение на 8 пикселей в ту же сторону.
            on_ice = False
            for obstacle in obstacles:
                if isinstance(obstacle, Ice) and self.rect.colliderect(obstacle.rect):
                    on_ice = True
                    break

            if on_ice:
                opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}
                if old_direction in opposite and self.direction == opposite[old_direction]:
                    # Воспроизводим звук льда
                    ice_sound.play()
                    # Продолжаем инерционное движение на 8 пикселей в выбранном направлении
                    if self.direction == "up":
                        self.rect.y -= 16
                    elif self.direction == "down":
                        self.rect.y += 16
                    elif self.direction == "left":
                        self.rect.x -= 16
                    elif self.direction == "right":
                        self.rect.x += 16
            # Базовая проверка коллизий с другими танками
            for tank in tank_group:
                if tank != self and self.rect.colliderect(tank.rect):
                    self.rect = old_rect
                    break

            self.is_moving = (old_rect.x != self.rect.x or old_rect.y != self.rect.y)
            self._animate()
            
            # Отображение прямоугольников вокруг объектов
            if show_masks:
                for obstacle in obstacles:
                    pygame.draw.rect(screen, (255, 255, 0), obstacle.rect, 1)
        else:
            self._animate()

    def _animate(self):
        global current_player_sound
        now = pygame.time.get_ticks()
        if self.is_moving:
            if now - self.last_update > self.animation_interval:
                self.last_update = now
                self.current_sprite = (self.current_sprite + 1) % 2
        else:
            self.current_sprite = 0
            # Если игрок не двигается:
            if self.is_player:
                # ### ИЗМЕНЕНИЕ: проверяем, есть ли ещё враги
                if enemies_remaining_level > 0:
                    # Если враги есть – можно играть stand
                    if current_player_sound != "stand":
                        player_sound_channel.stop()
                        player_sound_channel.play(stand_sound, loops=-1)
                        current_player_sound = "stand"
                else:
                    # Врагов нет – не даём включаться звуку stand
                    if current_player_sound == "stand":
                        player_sound_channel.stop()
                        current_player_sound = None

            self.current_sprite = 0
        self.image = self.sprites[self.direction][self.current_sprite]

    def shoot(self):
        if game_over:  # Блокируем стрельбу при game_over
            return

        now = pygame.time.get_ticks()
        
        # Проверяем, есть ли активные пули
        if self.is_player:
            active_bullets = player_bullets
        else:
            active_bullets = enemy_bullets

        if any(bullet.owner == ("player" if self.is_player else "enemy") for bullet in active_bullets):
            return  # Если есть активные пули, не стреляем

        if not self.can_double_shot:
            # Обычный выстрел (кулдаун 500 мс)
            if now >= self.shoot_cooldown and self.is_alive:
                self._do_shot()
                self.shoot_cooldown = now + 100
        else:
            # Двойной выстрел
            if (now - self.last_shot_time) > 100:
                self.shots_in_burst = 0
            
            if now >= self.shoot_cooldown and self.is_alive:
                self._do_shot()
                self.shots_in_burst += 100
                self.last_shot_time = now
                
                if self.shots_in_burst >= 2:
                    # после второго выстрела кулдаун 500
                    self.shoot_cooldown = now + 100
                    self.shots_in_burst = 0
                else:
                    # между первым и вторым — не более 100 мс
                    self.shoot_cooldown = now + 100

    def _do_shot(self):
        """Непосредственно создаёт пулю."""
        offset = -2  # Смещение от края танка
        if self.direction == "up":
            bullet_x = self.rect.centerx
            bullet_y = self.rect.top - offset
        elif self.direction == "down":
            bullet_x = self.rect.centerx
            bullet_y = self.rect.bottom + offset
        elif self.direction == "left":
            bullet_x = self.rect.left - offset
            bullet_y = self.rect.centery
        else:  # right
            bullet_x = self.rect.right + offset
            bullet_y = self.rect.centery

        bullet = Bullet(
            bullet_x, bullet_y,
            self.direction,
            owner="player" if self.is_player else "enemy",
            speed=self.bullet_speed
        )
        if self.is_player and self.armor_piercing:
            bullet.armor_piercing = True
        
        if self.is_player:
            player_bullets.add(bullet)
            shoot_sound.play()  # Проигрываем звук выстрела только для игрока
            do_rumble(0.2, 0.2, 150)
        else:
            enemy_bullets.add(bullet)
        
        all_sprites.add(bullet)

    def destroy(self):
        if self.is_player:
            death_sound.play()
        else:
            kill_sound.play()
        explosion = Explosion(self.rect.center)
        explosions.add(explosion)
        all_sprites.add(explosion)
        self.is_alive = False
        self.kill()
        tank_group.remove(self)

# =========================
# Класс Enemy – танк врага
# =========================
class Enemy(Tank):
    def __init__(self, x, y, initial_direction, enemy_type=1, armor_level=1):
        super().__init__(x, y, is_player=False, enemy_type=enemy_type)
        global enemy_counter
        self.change_direction_time = pygame.time.get_ticks() + random.randint(1000, 5000)
        self.speed = 2
        self.direction = initial_direction
        self.destroy_time = None
        self.enemy_type = enemy_type
        self.armor_level = armor_level
        self.path = []
        self.target = None
        self.last_position = self.rect.center
        self.stuck_time = 0
        self.max_stuck_duration = 5000
        self.distance_to_hq = float('inf')
        self.can_double_shot = False
        self.enemy_shoot_cooldown = 0
        self.stuck_counter = 0
        if enemy_type == 4:
            self.max_health = armor_level + 1
            self.health = self.max_health
            self._update_color()
        self.image = self.sprites[self.direction][self.current_sprite]
        self.rect = self.image.get_rect(center=self.rect.center)
        self.animation_interval = 15
        
        if enemy_type == 1:
            self.speed = 2
            self.bullet_speed = 5
            self.score_value = 100
        elif enemy_type == 2:
            self.speed = 3
            self.bullet_speed = 6
            self.score_value = 200
        elif enemy_type == 3:
            self.speed = 1
            self.bullet_speed = 10
            self.score_value = 300
        elif enemy_type == 4:
            self.speed = 1
            self.bullet_speed = 6
            self.armor_level = armor_level
            self.max_health = armor_level + 1
            self.health = self.max_health
            self.score_value = 400
            self._update_color()
        
        self.is_special = enemy_counter in [4, 11, 18]
        self.blink_state = False
        self.last_blink = 0

        # Добавляем случайный цвет для пути
        self.path_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    
    def choose_target(self):
        hq = next((spr for spr in obstacles if isinstance(spr, Headquarters)), None)
        if hq and not hq.destroyed:
            hq_distance = self.get_distance_to(hq.rect.center)
        else:
            hq_distance = float('inf')

        if player and player.is_alive:
            player_distance = self.get_distance_to(player.rect.center)
        else:
            player_distance = float('inf')

        if hq_distance < player_distance:
            self.target = hq.rect.center
            self.target_priority = 0.8  # Повышенный приоритет
        elif player and player.is_alive:
            self.target = player.rect.center
            self.target_priority = 0.4
        else:
            self.target = None
            self.target_priority = 0.0

    def get_distance_to(self, target):
        return ((self.rect.centerx - target[0]) ** 2 + (self.rect.centery - target[1]) ** 2) ** 0.5

    def shoot(self):
        if game_over:  # Блокируем стрельбу при game_over
            return

        now = pygame.time.get_ticks()
        
        # Проверяем, есть ли активные пули
        if self.is_player:
            active_bullets = player_bullets
        else:
            active_bullets = enemy_bullets

        if any(bullet.owner == ("player" if self.is_player else "enemy") for bullet in active_bullets):
            return  # Если есть активные пули, не стреляем

        if not self.is_player:
            if now < self.enemy_shoot_cooldown:
                return  # Если кулдаун врага не истек, не стреляем

        if not self.can_double_shot:
            # Обычный выстрел (кулдаун 500 мс)
            if now >= self.shoot_cooldown and self.is_alive:
                self._do_shot()
                self.shoot_cooldown = now + 100
                if not self.is_player:
                    self.enemy_shoot_cooldown = now + 1000  # Устанавливаем кулдаун для врагов
        else:
            # Двойной выстрел
            if (now - self.last_shot_time) > 100:
                self.shots_in_burst = 0
            
            if now >= self.shoot_cooldown and self.is_alive:
                self._do_shot()
                self.shots_in_burst += 100
                self.last_shot_time = now
                
                if self.shots_in_burst >= 2:
                    # после второго выстрела кулдаун 500
                    self.shoot_cooldown = now + 100
                    self.shots_in_burst = 0
                else:
                    # между первым и вторым — не более 100 мс
                    self.shoot_cooldown = now + 100
                if not self.is_player:
                    self.enemy_shoot_cooldown = now + 1000  # Устанавливаем кулдаун для врагов
    
    def _animate(self):
        now = pygame.time.get_ticks()
        if self.is_moving:
            if now - self.last_update > self.animation_interval:
                self.last_update = now
                self.current_sprite = (self.current_sprite + 1) % 2
        else:
            self.current_sprite = 0
        self.image = self.sprites[self.direction][self.current_sprite]

    def _update_color(self):
        if self.enemy_type == 4:
            if self.armor_level not in ARMOR_COLORS:
                return
            colors_list = ARMOR_COLORS[self.armor_level]
            index = self.max_health - self.health
            if index < 0: index = 0
            if index >= len(colors_list):
                index = len(colors_list) - 1
            color = colors_list[index]

            for direction in ["up", "down", "left", "right"]:
                new_frames = []
                base_frames = heavy_tank_base_sprites[direction]
                for bf in base_frames:
                    frame_copy = bf.copy()
                    frame_copy.fill(color, special_flags=pygame.BLEND_RGB_MULT)
                    new_frames.append(frame_copy)
                self.sprites[direction] = new_frames

            self.image = self.sprites[self.direction][self.current_sprite]
    
    def take_damage(self):
        global bonus_active
        if self.enemy_type == 4:
            self.health -= 1
            if self.is_special and self.health == self.max_health - 1:
                # Спавн бонуса при первом попадании
                cols = GRID_COLS - 2
                rows = GRID_ROWS - 2
                rand_col = random.randint(1, cols)
                rand_row = random.randint(1, rows)
                bonus_x = LEFT_MARGIN + (rand_col * CELL_SIZE) - CELL_SIZE//2
                bonus_y = TOP_MARGIN + (rand_row * CELL_SIZE) - CELL_SIZE//2
                Bonus((bonus_x, bonus_y))
                bonus_active = True
                self.is_special = False

            if self.health <= 0:
                self.destroy()
                return True
            else:
                minus_armor_sound.play()
                self._update_color()
                return False
        else:
            self.destroy()
            return True
              
    def destroy(self, no_score=False):
        global global_score, bonus_active
        if not self.is_alive:
            return

        self.is_alive = False
        self.kill()
        tank_group.remove(self)
        kill_sound.play()

        # Создаём взрыв
        if no_score:
            explosion = Explosion(self.rect.center, score_points=None, popup_duration=250)
        else:
            explosion = Explosion(self.rect.center, score_points=self.score_value, popup_duration=250)
        explosions.add(explosion)
        all_sprites.add(explosion)

        ### Добавляем вибрацию, если убит "ручным" способом (не гранатой)
        # Средняя вибрация, например 0.5 силы, 300 мс:
        do_rumble(0.4, 0.4, 300)

        # Начисляем очки
        if not no_score:
            global_score += self.score_value

        # Уменьшаем счётчик врагов
        global enemies_remaining_level
        enemies_remaining_level -= 1

        # ### ИЗМЕНЕНИЕ: сразу создаём бонус (если танк был «специальным» и не тяжёлый),
        #   чтобы звук появления (bonus_appear_sound) проигрался моментально
        if self.is_special and self.enemy_type != 4 and not no_score:
            cols = GRID_COLS - 2
            rows = GRID_ROWS - 2
            rand_col = random.randint(1, cols)
            rand_row = random.randint(1, rows)
            bonus_x = LEFT_MARGIN + (rand_col * CELL_SIZE) - CELL_SIZE // 2
            bonus_y = TOP_MARGIN + (rand_row * CELL_SIZE) - CELL_SIZE // 2
            Bonus((bonus_x, bonus_y))
            bonus_active = True

    def handle_stuck(self):
        # Усовершенствованная система определения застревания
        if self.stuck_counter > 15:
            self.speed *= 1.2  # Временно увеличиваем скорость
            self.change_direction()
            self.stuck_counter = 0
            
            # Создаем временные проходы в препятствиях
            if random.random() < 0.3:
                for obstacle in obstacles:
                    if self.rect.colliderect(obstacle.rect):
                        if isinstance(obstacle, BrickWall):
                            obstacle.take_damage(Bullet(0,0, 'up', owner='enemy', speed=0))

    def ai_update(self):
        global enemy_stop, enemy_stop_end_time
        if enemy_stop:
            if pygame.time.get_ticks() < enemy_stop_end_time:
                return
            else:
                enemy_stop = False  # сброс эффекта

        old_rect = self.rect.copy()
        now = pygame.time.get_ticks()

        # Проверка на застревание
        if self.rect.center == self.last_position:
            self.stuck_time += now - self.last_update
        else:
            self.stuck_time = 0
            self.last_position = self.rect.center

        if self.stuck_time > self.max_stuck_duration:
            self.handle_stuck()  # Используем функцию handle_stuck
            self.stuck_time = 0

        # Вероятность стремления к игроку или штабу
        if not self.path or random.random() < 0.01:  # Уменьшаем вероятность случайного изменения пути
            self.choose_target()  # Используем функцию choose_target

            if self.target:
                self.path = find_path(self.rect.center, self.target)

        # Если путь найден, следуем по нему
        if self.path:
            next_step = self.path[0]
            if next_step[1] < self.rect.centery:
                self.direction = "up"
            elif next_step[1] > self.rect.centery:
                self.direction = "down"
            elif next_step[0] < self.rect.centerx:
                self.direction = "left"
            elif next_step[0] > self.rect.centerx:
                self.direction = "right"

            if self.rect.center == next_step:
                self.path.pop(0)
                if not self.path:
                    self.target = None
                    self.path = []  # Очищаем путь, когда цель достигнута

        if self.direction == "up":
            self.rect.y -= self.speed
        elif self.direction == "down":
            self.rect.y += self.speed
        elif self.direction == "left":
            self.rect.x -= self.speed
        elif self.direction == "right":
            self.rect.x += self.speed

        if not FIELD_RECT.contains(self.rect):
            self.rect = old_rect
            self.direction = random.choices(["up", "down", "left", "right"], weights=[1, 3, 1, 1])[0]
        for tank in tank_group:
            if tank != self and self.rect.colliderect(tank.rect):
                self.rect = old_rect
                self.direction = random.choices(["up", "down", "left", "right"], weights=[1, 3, 1, 1])[0]
                break
        for obstacle in obstacles:
            if isinstance(obstacle, Ice):
                continue  # враги могут ездить по льду
            if hasattr(obstacle, 'mask'):
                tank_mask = pygame.mask.from_surface(self.image)
                offset = (obstacle.rect.x - self.rect.x, obstacle.rect.y - self.rect.y)
                if tank_mask.overlap(obstacle.mask, offset):
                    self.rect = old_rect
                    self.direction = random.choices(["up", "down", "left", "right"], weights=[1, 3, 1, 1])[0]
                    break
            else:
                if self.rect.colliderect(obstacle.rect):
                    self.rect = old_rect
                    self.direction = random.choices(["up", "down", "left", "right"], weights=[1, 3, 1, 1])[0]
                    break
        self.rect.clamp_ip(FIELD_RECT)
        
        # Обновляем флаг движения: если позиция изменилась – считаем, что танк движется
        self.is_moving = (old_rect.x != self.rect.x or old_rect.y != self.rect.y)
        
        # Запускаем анимацию (она теперь будет проверять self.is_moving)
        self._animate()

        for obstacle in obstacles:
            if isinstance(obstacle, Ice):
                continue  # враги могут ездить по льду
            if self.rect.colliderect(obstacle.rect):
                self.rect = old_rect
                self.direction = random.choice(["up", "down", "left", "right"])
                break

        # Проверка на наличие кирпичной стены перед врагом
        if random.random() < 0.9:  # Вероятность 90%
            for obstacle in obstacles:
                if isinstance(obstacle, BrickWall):
                    if self.direction == "up" and self.rect.top > obstacle.rect.bottom and self.rect.left < obstacle.rect.right and self.rect.right > obstacle.rect.left:
                        self.shoot()
                    elif self.direction == "down" and self.rect.bottom < obstacle.rect.top and self.rect.left < obstacle.rect.right and self.rect.right > obstacle.rect.left:
                        self.shoot()
                    elif self.direction == "left" and self.rect.left > obstacle.rect.right and self.rect.top < obstacle.rect.bottom and self.rect.bottom > obstacle.rect.top:
                        self.shoot()
                    elif self.direction == "right" and self.rect.right < obstacle.rect.left and self.rect.top < obstacle.rect.bottom and self.rect.bottom > obstacle.rect.top:
                        self.shoot()

        # Мерцание для специальных танков (включая получивших урон не-тяжелых)
        if self.is_special:
            now = pygame.time.get_ticks()
            if now - self.last_blink > 200:
                self.blink_state = not self.blink_state
                self.last_blink = now
            if self.blink_state:
                self.image = bonus_enemy_sprites[self.enemy_type][self.direction][self.current_sprite]
            else:
                self.image = self.sprites[self.direction][self.current_sprite]

        if random.random() < 0.02:
            self.shoot()

        self.last_update = now  # Обновляем время последнего обновления

# =========================
# Класс Bullet – пуля
# =========================
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner, speed=5):
        super().__init__()
        self.image = bullet_sprites[direction]
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed  # Добавлен параметр скорости
        self.direction = direction
        self.owner = owner
        self.armor_piercing = False

    def update(self):
        old_pos = self.rect.center
        if self.owner == "enemy":
            if self.check_hq_collision():
                return
        step = 1  # Двигаем пулю по 1 пикселю за шаг
        dx, dy = 0, 0
        if self.direction == "up":
            dy = -step
        elif self.direction == "down":
            dy = step
        elif self.direction == "left":
            dx = -step
        elif self.direction == "right":
            dx = step

        # Проверяем коллизии на каждом микрошаге
        for _ in range(self.speed):
            self.rect.x += dx
            self.rect.y += dy

            # Проверка столкновений
            if self.check_collision():
                return

        # Новая проверка попадания в штаб
        if check_hq_hit(self):
            for hq in obstacles:
                if isinstance(hq, Headquarters) and not hq.destroyed:
                    do_rumble(1.0, 1.0, 1000)
                    hq.destroy()
                    self.kill()
                    return

        # Проверяем столкновение с препятствиями с использованием collide_map
        # Если пуля уходит за пределы игрового поля,
        # то для пуль игрока проигрываем звук, для вражеских — нет
        if not FIELD_RECT.collidepoint(self.rect.center):
            if self.owner == "player":
                wall_sound.play()
            create_hit_explosion(old_pos)
            self.kill()

    def check_hq_collision(self):
        hq = next((spr for spr in obstacles if isinstance(spr, Headquarters)), None)
        if hq and self.rect.colliderect(hq.rect):
            do_rumble(1.0, 1.0, 1000)
            hq.destroy()
            self.kill()
            return True
        return False

    def check_collision(self):
        old_pos = self.rect.center
        # Первым делом проверяем столкновение с HQ
        hq_collision = pygame.sprite.spritecollideany(self, obstacles, 
            collided=lambda spr, _: isinstance(spr, Headquarters))
        if hq_collision:
            hq_collision.destroy()
            self.kill()
            return True

        hits = pygame.sprite.spritecollide(self, obstacles, False, pygame.sprite.collide_mask)
        for obstacle in hits:
            if isinstance(obstacle, BrickWall):
                if obstacle.take_damage(self):
                    create_hit_explosion(old_pos)
                    self.kill()
                    return True
            # Бетонная стена
            elif isinstance(obstacle, ConcreteWall):
                # Если пуля от игрока и его уровень прокачки 4 – разрушаем элемент (аналогично кирпичной стене)
                explosion_created = False
                if self.owner == "player" and player_upgrade_level == 4:
                    if obstacle.take_damage(self):  # Реализуйте аналогичную логику take_damage для ConcreteWall
                        if not explosion_created:
                            create_hit_explosion(self.rect.center)
                            explosion_created = True
                        self.kill()
                        return
                # В противном случае — воспроизводим стандартный звук столкновения и эффект взрыва
                if self.owner == "player":
                    wall_sound.play()
                    if not explosion_created:
                        create_hit_explosion(self.rect.center)
                        explosion_created = True
                self.kill()
                return

            # Вода – пулям разрешается лететь над препятствием, пропускаем его
            elif isinstance(obstacle, Water):
                continue

            # Лёд – пули пролетают над ним, игнорируем
            elif isinstance(obstacle, Ice):
                continue

            else:
                self.kill()
                return
        return False

# =========================
# Класс для спрайта завершения игры
# =========================
class GameOverSprite(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = get_sprite(576, 367, 64, 32).convert_alpha()
        self.rect = self.image.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT+32))
        self.speed = 2
        self.target_y = WINDOW_HEIGHT // 2
        self.arrived = False
        self.arrival_time = 0

    def update(self):
        if not self.arrived:
            self.rect.y -= self.speed
            if self.rect.centery <= self.target_y:
                self.arrived = True
                self.arrival_time = pygame.time.get_ticks()

# =========================
# Функция запуска завершения игры
# =========================
def start_game_over_sequence():
    global game_over, game_over_sprite, game_over_phase, player_lives, player, paused, player_upgrade_level, current_player_sound
    game_over = True
    player_upgrade_level = 1  # Сбрасываем уровень прокачки
    game_over_phase = 0
    game_over_sprite = GameOverSprite()
    
    # Блокируем управление
    if player:
        player.speed = 0
        player.bullet_speed = 0
        player.is_alive = False
        
    # Останавливаем все звуки
    current_player_sound = None  # Сбросить состояние звука

    player_respawn_time = float('inf')

def update_grid_after_spawn():
    # При появлении нового врага выбираем первую ячейку (по порядку удаления) которая ещё True и устанавливаем False
    for i in range(len(grid_status)):
        if grid_status[i]:
            grid_status[i] = False
            break

def reset_grid():
    global grid_status
    grid_status = [True] * 20

def next_level():
    global player, current_player_sound, current_level, enemies_to_spawn, enemies_remaining_level, enemy_counter, player_respawn_time, level_complete_time
    player_sound_channel.stop()
    current_player_sound = None
    if player is not None:
        player.kill()
    player = None
    current_level += 1
    level_complete_time = None
    # После убийства всех врагов уровня, переходим на следующий уровень
    level_transition(current_level)
    enemies_to_spawn = 20
    enemies_remaining_level = 20
    enemy_counter = 1
    reset_grid()
    # Удаляем все оставшиеся вражеские спрайты, если таковые остались
    for enemy in list(enemies):
        enemy.kill()
    # Сбрасываем время респауна игрока, чтобы условие в основном цикле сработало
    player_respawn_time = pygame.time.get_ticks()

def spawn_player_callback(pos):
    global player, shield_end_time
    now = pygame.time.get_ticks()
    ### ИЗМЕНЕНИЕ: передаём upgrade_level=player_upgrade_level
    player = Tank(pos[0], pos[1], is_player=True, upgrade_level=player_upgrade_level)
    # Включаем защитное поле на 4 секунды после появления
    player.shield_active = True
    player.shield_start = now
    shield_end_time = now + 4000
    all_sprites.add(player)
    tank_group.add(player)

def can_spawn_at(pos):
    # Создаем прямоугольник, центр которого в pos, размер 32x32
    temp_rect = pygame.Rect(pos[0] - 16, pos[1] - 16, 32, 32)
    # Если прямоугольник пересекается с прямоугольником любого танка — спавн невозможен
    return not any(tank.rect.colliderect(temp_rect) for tank in tank_group)

def get_available_spawn_cell():
    # Перебираем ячейки в случайном порядке
    free_positions = [pos for pos in spawn_positions if not spawn_occupancy[pos]]
    random.shuffle(free_positions)
    for pos in free_positions:
        if can_spawn_at(pos):
            return pos
    return None

# =========================
# Функция обратного вызова для появления врага
# =========================
def spawn_enemy_callback(pos):
    global enemies_to_spawn, enemy_counter, bonus_active
    
    allowed = ["down", "right"]
    if pos[0] == LEFT_MARGIN + 12 * CELL_SIZE + 16:
        allowed = ["left", "down"]
    elif pos[0] == LEFT_MARGIN + 6 * CELL_SIZE + 16:
        allowed = ["left", "down", "right"]
    
    initial_direction = random.choice(allowed)
    
    # Определение типа танка
    enemy_type = 1
    # Генерация врагов с разными характеристиками
    if enemies_to_spawn > 15:
        enemy_type = random.choices([1,2,3], weights=[5,3,2])[0]  # Обычные танки
    elif enemies_to_spawn > 5:
        enemy_type = random.choices([2,3,4], weights=[4,3,3])[0]  # Средние
    else:
        enemy_type = 4 if random.random() < 0.7 else 3  # Тяжелые и скорострельные
        
    enemy = Enemy(pos[0], pos[1], initial_direction, enemy_type=enemy_type)
    if enemy_type == 4:
        enemy.speed = 1.5
        enemy.target_priority = 0.8  # Тяжелые танки целятся в штаб
    
    # Создаём временного врага (пока не добавляем в группы).
    if enemy_type == 4:
        armor_level = random.randint(1, 3)
        temp_enemy = Enemy(pos[0], pos[1], initial_direction, enemy_type=4, armor_level=armor_level)
    else:
        temp_enemy = Enemy(pos[0], pos[1], initial_direction, enemy_type=enemy_type)

    # Проверяем, не столкнётся ли он с уже существующими танками (включая игрока)
    collided = False
    for t in tank_group:
        if t.rect.colliderect(temp_enemy.rect):
            collided = True
            break
    
    # Если коллизия есть — НЕ спавним
    if collided:
        temp_enemy.kill()  # удаляем временный объект
        # Освобождаем спавн-позицию
        spawn_occupancy[pos] = False
        return

    # Если коллизий нет – спавним официально
    # Если враг special -> уничтожаем предыдущий бонус
    if temp_enemy.is_special:
        for b in bonus_group:
            b.kill()
        bonus_active = False

    # Настройка скорости пуль у «скорострельного» танка
    if enemy_type == 3:
        temp_enemy.bullet_speed = 14

    enemies.add(temp_enemy)
    tank_group.add(temp_enemy)
    all_sprites.add(temp_enemy)
    enemy_counter += 1
    enemies_to_spawn -= 1
    update_grid_after_spawn()
    spawn_occupancy[pos] = False

# Функция загрузка уровня из файла
def load_level(level_num):
    obstacles.empty()
    forests.empty()
    hq_temp_walls.empty()

    try:
        with open(f"levels/{level_num:02d}", 'r') as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        print(f"Level {level_num} not found!")
        return

    # Словари для хранения объектов по координатам
    brick_walls = {}
    concrete_walls = {}
    waters = {}
    forests_dict = {}
    ices = {}

    for line in lines:
        parts = line.split(',')
        if parts[0] == 'hq':
            # Создаем штаб
            grid_x, grid_y = int(parts[1]), int(parts[2])
            x = LEFT_MARGIN + grid_x * CELL_SIZE
            y = TOP_MARGIN + grid_y * CELL_SIZE
            hq = Headquarters(x, y)
            obstacles.add(hq)
            all_sprites.add(hq)
        else:
            grid_x, grid_y = int(parts[0]), int(parts[1])
            part = parts[2]
            obj_type = parts[3]

            x = LEFT_MARGIN + grid_x * CELL_SIZE
            y = TOP_MARGIN + grid_y * CELL_SIZE

            if obj_type == 'brick':
                if (x, y) not in brick_walls:
                    brick_walls[(x, y)] = []
                brick_walls[(x, y)].append(part)
            elif obj_type == 'concrete':
                if (x, y) not in concrete_walls:
                    concrete_walls[(x, y)] = []
                concrete_walls[(x, y)].append(part)
            elif obj_type == 'water':
                if (x, y) not in waters:
                    waters[(x, y)] = []
                waters[(x, y)].append(part)
            elif obj_type == 'forest':
                if (x, y) not in forests_dict:
                    forests_dict[(x, y)] = []
                forests_dict[(x, y)].append(part)
            elif obj_type == 'ice':
                if (x, y) not in ices:
                    ices[(x, y)] = []
                ices[(x, y)].append(part)

    # Создаем объекты из словарей
    for (x, y), parts in brick_walls.items():
        BrickWall(x, y, active_cells=parts).add(obstacles, all_sprites)
    for (x, y), parts in concrete_walls.items():
        ConcreteWall(x, y, active_cells=parts).add(obstacles, all_sprites)
    for (x, y), parts in waters.items():
        Water(x, y, active_cells=parts).add(obstacles, all_sprites)
    for (x, y), parts in forests_dict.items():
        Forest(x, y, active_cells=parts).add(forests, all_sprites)
    for (x, y), parts in ices.items():
        Ice(x, y, active_cells=parts).add(obstacles, all_sprites)

# =========================
# Функция перехода на уровень (экран STAGE)
# =========================
def level_transition(level):
    global hq_wall_positions, selecting

    if level > 1:
        final_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        final_surface.fill((117, 117, 117))  # затемнённые отступы
        pygame.draw.rect(final_surface, (0, 0, 0), FIELD_RECT)

    clock = pygame.time.Clock()
    selected_level = level
    last_change_time = 0
    acceleration_delay = 500  # Задержка перед ускоренным изменением
    acceleration_interval = 90  # Интервал при ускорении
    last_start_press_time = pygame.time.get_ticks()  # Время последнего нажатия кнопки start

    while selecting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        keys = pygame.key.get_pressed()
        joystick_buttons = {}
        if joystick:
            mapping = button_mapping[joystick_type]
            joystick_buttons['left'] = joystick.get_button(mapping['B'])
            joystick_buttons['right'] = joystick.get_button(mapping['A'])
            joystick_buttons['start'] = joystick.get_button(mapping['start'])
        
        # Изменение уровня
        change_amount = 0
        now = pygame.time.get_ticks()
        if last_change_time == 0:
            if keys[pygame.K_LEFT] or joystick_buttons.get('left'):
                change_amount -= 1
                last_change_time = now
            if keys[pygame.K_RIGHT] or joystick_buttons.get('right'):
                change_amount += 1
                last_change_time = now
        else:
            # Ускоренное изменение после задержки
            if now - last_change_time > acceleration_delay:
                if keys[pygame.K_LEFT] or joystick_buttons.get('left'):
                    change_amount -= 1
                    last_change_time = now - acceleration_delay + acceleration_interval
                if keys[pygame.K_RIGHT] or joystick_buttons.get('right'):
                    change_amount += 1
                    last_change_time = now - acceleration_delay + acceleration_interval

        selected_level = max(1, min(35, selected_level + change_amount))
        
        # Подтверждение выбора
        if keys[pygame.K_SPACE] or keys[pygame.K_RETURN] or joystick_buttons.get('start'):
            # Проверяем время последнего нажатия кнопки start
            if now - last_start_press_time > 500:  # 500мс задержка
                selecting = False
                last_start_press_time = now
        
        # Отрисовка
        screen.fill((0, 0, 0))
        
        # Рассчитываем отступы
        level_digits = render_level_number(selected_level)
        total_width = 80 + (16 * len(level_digits))
        offset = 32 if selected_level < 10 else 16
        start_x = FIELD_RECT.left + (FIELD_RECT.width - total_width - offset) // 2
        start_y = FIELD_RECT.top + (FIELD_RECT.height - 14) // 2
        
        stage_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        stage_surface.fill((117, 117, 117))
        stage_surface.blit(stage_text_sprite, (start_x, start_y))
        
        digit_x = start_x + 80 + offset
        digit_y = start_y - 1
        for digit_sprite in level_digits:
            stage_surface.blit(digit_sprite, (digit_x, digit_y))
            digit_x += 16
        
        screen.blit(stage_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)
    
    # Продолжаем обычную загрузку уровня
    selected_level = max(1, min(35, selected_level))  # Ограничение уровней от 1 до 35

    # 0. Очистка всех спрайтов
    global all_sprites, tank_group, enemies, spawn_group, explosions, player_bullets, enemy_bullets
    all_sprites.empty()
    tank_group.empty()
    enemies.empty()
    spawn_group.empty()
    explosions.empty()
    player_bullets.empty()
    enemy_bullets.empty()
    bonus_group.empty()
    obstacles.empty()
    forests.empty()

    # Загрузка выбранного уровня
    load_level(selected_level)

    #
    # --- Сокращение анимации закрытия до 600 мс (было 1200) ---
    #
    anim_duration = 600
    start_anim = pygame.time.get_ticks()
    
    if level > 1:
        while True:
            now = pygame.time.get_ticks()
            elapsed = now - start_anim
            if elapsed > anim_duration:
                break
                
            ratio = elapsed / anim_duration
            fill_height = int((WINDOW_HEIGHT // 2) * ratio)
            
            screen.fill((0, 0, 0))
            pygame.draw.rect(screen, (117, 117, 117), (0, 0, WINDOW_WIDTH, fill_height))
            pygame.draw.rect(
                screen, (117, 117, 117),
                (0, WINDOW_HEIGHT - fill_height, WINDOW_WIDTH, fill_height)
            )
            
            pygame.display.flip()
            pygame.time.delay(16)

    # 1. Рисуем надпись STAGE + номер уровня на центре игрового поля
    level_digits = render_level_number(selected_level)
    total_width = 80 + (16 * len(level_digits))
    offset = 32 if selected_level < 10 else 16
    start_x = FIELD_RECT.left + (FIELD_RECT.width - total_width - offset) // 2
    start_y = FIELD_RECT.top + (FIELD_RECT.height - 14) // 2
    
    stage_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    stage_surface.fill((117, 117, 117))
    stage_surface.blit(stage_text_sprite, (start_x, start_y))
    
    digit_x = start_x + 80 + offset
    digit_y = start_y - 1
    for digit_sprite in level_digits:
        stage_surface.blit(digit_sprite, (digit_x, digit_y))
        digit_x += 16
    
    start_sound.play()
    screen.blit(stage_surface, (0, 0))
    pygame.display.flip()

    # Ждем завершения звука
    pygame.time.wait(3000)

    anim_duration = 500
    start_anim = pygame.time.get_ticks()

    # Готовим финальный кадр
    mask_surface = pygame.Surface((FIELD_RECT.size), pygame.SRCALPHA)
    final_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    final_surface.fill((117, 117, 117))
    pygame.draw.rect(final_surface, (0, 0, 0), FIELD_RECT)

    while True:
        now = pygame.time.get_ticks()
        elapsed = now - start_anim
        if elapsed > anim_duration:
            break

        ratio = elapsed / anim_duration
        current_height = int((FIELD_RECT.height // 2) * (1 - ratio))

        mask_surface.fill((117, 117, 117, 255))
        pygame.draw.rect(
            mask_surface, (0, 0, 0, 0),
            (0, current_height, FIELD_RECT.width, FIELD_RECT.height - 2 * current_height)
        )

        screen.blit(final_surface, (0, 0))
        screen.blit(mask_surface, FIELD_RECT.topleft)
        pygame.display.flip()
        pygame.time.delay(16)

    screen.blit(final_surface, (0, 0))

    # Сохраняем позиции стен штаба
    hq_wall_positions = [
        (LEFT_MARGIN + 5*CELL_SIZE, TOP_MARGIN + 12*CELL_SIZE, ["br", "tr"]),
        (LEFT_MARGIN + 5*CELL_SIZE, TOP_MARGIN + 11*CELL_SIZE, ["br"]),
        (LEFT_MARGIN + 6*CELL_SIZE, TOP_MARGIN + 11*CELL_SIZE, ["bl", "br"]),
        (LEFT_MARGIN + 7*CELL_SIZE, TOP_MARGIN + 11*CELL_SIZE, ["bl"]),
        (LEFT_MARGIN + 7*CELL_SIZE, TOP_MARGIN + 12*CELL_SIZE, ["bl", "tl"])
    ]

    # Создаем кирпичные стены
    for x, y, cells in hq_wall_positions:
        wall = BrickWall(x, y, active_cells=cells)
        obstacles.add(wall)
        all_sprites.add(wall)

    # Создание штаба
    hq_x = LEFT_MARGIN + 6 * CELL_SIZE
    hq_y = TOP_MARGIN + 12 * CELL_SIZE
    hq = Headquarters(hq_x, hq_y)
    obstacles.add(hq)  # Добавляем HQ в группу препятствий
    all_sprites.add(hq)

    pygame.display.flip()

# =========================
# Обработка бонуса HQ Boost
# =========================
def activate_hq_boost():
    global hq_boost_active, hq_boost_end_time, hq_original_walls
    hq_boost_active = True
    hq_boost_end_time = pygame.time.get_ticks() + 15000  # 15 секунд
    
    # Сохраняем оригинальные стены
    hq_original_walls = [wall for wall in obstacles if isinstance(wall, BrickWall) and wall.rect.topleft in [(x,y) for x,y,_ in hq_wall_positions]]
    
    # Удаляем оригинальные кирпичные стены
    for wall in hq_original_walls:
        wall.kill()
    
    # Создаем временные бетонные стены
    for x, y, cells in hq_wall_positions:
        concrete_wall = ConcreteWall(x, y, active_cells=cells)
        hq_temp_walls.add(concrete_wall)
    
    obstacles.add(hq_temp_walls)
    all_sprites.add(hq_temp_walls)

def deactivate_hq_boost():
    global hq_boost_active, blink_state
    hq_boost_active = False
    blink_state = False
    
    # Удаляем временные стены
    for wall in hq_temp_walls:
        wall.kill()
    
    # Восстанавливаем оригинальные стены
    for x, y, cells in hq_wall_positions:
        new_wall = BrickWall(x, y, active_cells=cells)
        obstacles.add(new_wall)
        all_sprites.add(new_wall)

# =========================
# Главное меню выбора режима (исправлено управление джойстиком)
# =========================
def main_menu():
    global selecting
    selecting = True
    title_font = pygame.font.SysFont("consolas", 48, bold=True)
    option_font = pygame.font.SysFont("consolas", 32)
    title_text = title_font.render("Battle City", True, (255, 0, 0))
    option_texts = [
        option_font.render("1 PLAYER", True, (255, 255, 255)),
        option_font.render("2 PLAYERS", True, (255, 255, 255))
    ]
    title_rect = title_text.get_rect()
    spacing = 20
    total_menu_height = title_rect.height + spacing + sum(opt.get_rect().height for opt in option_texts) + spacing * (len(option_texts) - 1)
    final_menu_y = (WINDOW_HEIGHT - total_menu_height) // 2
    menu_y = WINDOW_HEIGHT  # стартуем за пределами окна (снизу)
    slide_duration = 1000
    menu_start_time = pygame.time.get_ticks()
    selection_index = 0
    clock = pygame.time.Clock()
    selected_mode = None
    
    # Параметры анимации для индикатора выбора (танка)
    indicator_anim_index = 0
    last_indicator_anim_update = pygame.time.get_ticks()
    # Массив спрайтов танка для выбранного направления (например, "right")
    indicator_sprites = player_sprites_level1["right"]

    while selected_mode is None:
        now = pygame.time.get_ticks()
        dt = now - menu_start_time
        if dt >= 1000:
            t = dt - 1000
            if t < slide_duration:
                menu_y = WINDOW_HEIGHT - ((WINDOW_HEIGHT - final_menu_y) * (t / slide_duration))
            else:
                menu_y = final_menu_y

        # Обновляем анимацию индикатора каждые 60 мс
        if now - last_indicator_anim_update >= 60:
            indicator_anim_index = (indicator_anim_index + 1) % len(indicator_sprites)
            last_indicator_anim_update = now

        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Обработка клавиатуры
            if event.type == pygame.KEYDOWN:
                if now >= menu_start_time + 1000 + slide_duration:
                    if event.key == pygame.K_UP:
                        selection_index = (selection_index - 1) % len(option_texts)
                    if event.key == pygame.K_DOWN:
                        selection_index = (selection_index + 1) % len(option_texts)
                    if event.key == pygame.K_SPACE:
                        selected_mode = selection_index
            # Обработка джойстика
            if event.type == pygame.JOYBUTTONDOWN:
                if now >= menu_start_time + 1000 + slide_duration:
                    mapping = button_mapping[joystick_type]
                    if event.button == mapping['up']:
                        selection_index = (selection_index - 1) % len(option_texts)
                    elif event.button == mapping['down']:
                        selection_index = (selection_index + 1) % len(option_texts)
                    elif event.button == mapping['start']:
                        selected_mode = selection_index
            if event.type == pygame.JOYHATMOTION:
                if now >= menu_start_time + 1000 + slide_duration:
                    hat = event.value
                    mapping = button_mapping[joystick_type]
                    if hat == mapping['hat_up']:
                        selection_index = (selection_index - 1) % len(option_texts)
                    elif hat == mapping['hat_down']:
                        selection_index = (selection_index + 1) % len(option_texts)

        # Рисуем меню
        menu_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        menu_surface.fill((0, 0, 0))
        title_x = (WINDOW_WIDTH - title_rect.width) // 2
        menu_surface.blit(title_text, (title_x, menu_y))
        current_y = menu_y + title_rect.height + spacing
        for i, opt in enumerate(option_texts):
            opt_rect = opt.get_rect()
            opt_x = (WINDOW_WIDTH - opt_rect.width) // 2
            menu_surface.blit(opt, (opt_x, current_y))
            # Если этот пункт выбран, рисуем анимированный индикатор (танк) слева от него
            if i == selection_index:
                indicator_rect = indicator_sprites[indicator_anim_index].get_rect()
                indicator_rect.midright = (opt_x - 10, current_y + opt_rect.height // 2)
                menu_surface.blit(indicator_sprites[indicator_anim_index], indicator_rect)
            current_y += opt_rect.height + spacing

        screen.fill((0, 0, 0))
        screen.blit(menu_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)
    return selected_mode

# =========================
# Запуск главного меню
# =========================
mode = main_menu()  # выбор режима

# После меню – переход на уровень (уровень 1)
level_transition(1)

# =========================
# Основной игровой цикл
# =========================
player_respawn_time = 0
player = None  # игрок появляется сразу без анимации появления

next_spawn_time = pygame.time.get_ticks() + random.randint(1000, 7000)

spawn_occupancy = { pos: False for pos in spawn_positions }

current_player_sound = None
paused = False
pause_blink = False
last_blink_time = 0
shield_end_time = 0
paused_frame = None   # Новая переменная для хранения "замороженного" кадра при паузе
level_complete_time = None

clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            print(f"Key pressed: {pygame.key.name(event.key)}")
            if event.key == pygame.K_ESCAPE:
                paused = not paused
                pause_sound.play()
                if paused:
                    player_sound_channel.stop()
                    current_player_sound = None
                else:
                    # при выходе из паузы звук "stand" не включается до движения
                    current_player_sound = None
                    paused_frame = None  # очищаем замороженный кадр при выходе из паузы
            if not paused:
                if event.key == pygame.K_SPACE and player is not None:
                    player.shoot()
                if event.key == pygame.K_F1 and player is not None:
                    player.shield_active = not player.shield_active
                    player.shield_unlimited = True  # Бесконечный щит
                    if player.shield_active:
                        player.shield_start = pygame.time.get_ticks()
                        shield_end_time = float('inf')  # Очень большое время
                    else:
                        shield_end_time = 0
                if event.key == pygame.K_F2:
                    show_grid = not show_grid
                if event.key == pygame.K_F3:
                    show_masks = not show_masks  # Переключаем отображение масок
                if event.key == pygame.K_F4:
                    show_paths = not show_paths  # Переключаем отображение пути
        if event.type == pygame.JOYHATMOTION:
            # Получаем значение D-pad:
            hat = event.value  # tuple (x, y)
            print(f"Joystick D-pad: {hat}")
            # Обновляем словарь input_keys по данным D-pad
            input_keys = {
                pygame.K_UP: hat[1] == 1,
                pygame.K_DOWN: hat[1] == -1,
                pygame.K_LEFT: hat[0] == -1,
                pygame.K_RIGHT: hat[0] == 1
            }
            if player is not None:
                player.update(input_keys)
            # Вы можете сохранить его в глобальной переменной, например, joystick_hat = hat
        if event.type == pygame.JOYBUTTONDOWN:
            mapping = button_mapping[joystick_type]
            print(f"Joystick button pressed: {event.button}")
            for key, value in mapping.items():
                if event.button == value:
                    print(f"Mapped button: {key}")
            if event.button == mapping['start']:
                paused = not paused
                pause_sound.play()
                if paused:
                    player_sound_channel.stop()
                    current_player_sound = None
                else:
                    current_player_sound = None
                    paused_frame = None
            elif event.button == mapping['back'] and not paused:
                if player is not None:
                    player.shield_active = not player.shield_active
                    player.shield_unlimited = True
                    if player.shield_active:
                        player.shield_start = pygame.time.get_ticks()
                        shield_end_time = float('inf')
                    else:
                        shield_end_time = 0
            elif not paused and player is not None and event.button in [mapping['A'], mapping['B']]:
                player.shoot()

    if not paused:
        now = pygame.time.get_ticks()
        # Спавн врагов
        if now >= next_spawn_time and (len(enemies) + len(spawn_group)) < 4 and enemies_to_spawn > 0:
            chosen_pos = get_available_spawn_cell()
            if chosen_pos is not None:
                spawn_occupancy[chosen_pos] = True
                spawn_anim = SpawnAnimation(chosen_pos, spawn_enemy_callback)
                spawn_group.add(spawn_anim)
                all_sprites.add(spawn_anim)
            if len(enemies) < 2:
                next_spawn_time = now + random.randint(500, 2000)  # Сокращаем время появления новых врагов
            else:
                next_spawn_time = now + random.randint(1000, 7000)
        
        if enemy_stop:
            if now < enemy_stop_end_time:
                if now >= time_stop_rumble_next:
                    do_rumble(0.2, 0.2, 150)
                    time_stop_rumble_next = now + 1000
            else:
                enemy_stop = False

        # Получаем состояние клавиатуры
        keys = pygame.key.get_pressed()
        input_keys = {
            pygame.K_UP: keys[pygame.K_UP],
            pygame.K_DOWN: keys[pygame.K_DOWN],
            pygame.K_LEFT: keys[pygame.K_LEFT],
            pygame.K_RIGHT: keys[pygame.K_RIGHT],
            pygame.K_w: keys[pygame.K_w],
            pygame.K_a: keys[pygame.K_a],
            pygame.K_s: keys[pygame.K_s],
            pygame.K_d: keys[pygame.K_d]
        }

        # Если джойстик подключён, обновляем словарь input_keys по данным D-pad
        if joystick is not None:
            mapping = button_mapping[joystick_type]
            if joystick_type == "default":
                hat = joystick.get_hat(0)
                if hat == mapping['hat_up']:
                    input_keys[pygame.K_UP] = True
                    input_keys[pygame.K_w] = True
                elif hat == mapping['hat_down']:
                    input_keys[pygame.K_DOWN] = True
                    input_keys[pygame.K_s] = True
                if hat == mapping['hat_left']:
                    input_keys[pygame.K_LEFT] = True
                    input_keys[pygame.K_a] = True
                elif hat == mapping['hat_right']:
                    input_keys[pygame.K_RIGHT] = True
                    input_keys[pygame.K_d] = True
            if 'up' in mapping and mapping['up'] < joystick.get_numbuttons() and joystick.get_button(mapping['up']):
                input_keys[pygame.K_UP] = True
                input_keys[pygame.K_w] = True
            elif 'down' in mapping and mapping['down'] < joystick.get_numbuttons() and joystick.get_button(mapping['down']):
                input_keys[pygame.K_DOWN] = True
                input_keys[pygame.K_s] = True
            if 'left' in mapping and mapping['left'] < joystick.get_numbuttons() and joystick.get_button(mapping['left']):
                input_keys[pygame.K_LEFT] = True
                input_keys[pygame.K_a] = True
            elif 'right' in mapping and mapping['right'] < joystick.get_numbuttons() and joystick.get_button(mapping['right']):
                input_keys[pygame.K_RIGHT] = True
                input_keys[pygame.K_d] = True
        if player is not None:
            player.update(input_keys)
        player_bullets.update()
        enemy_bullets.update()
        for enemy in enemies:
            enemy.ai_update()
        spawn_group.update()
        explosions.update()
        popups.update()
        bonus_group.update()

        pygame.sprite.groupcollide(player_bullets, enemy_bullets, True, True)
        hits = pygame.sprite.groupcollide(player_bullets, enemies, True, False)
        for bullet, hit_enemies in hits.items():
            # Создаём короткую вспышку в месте попадания
            create_hit_explosion(bullet.rect.center)

            for enemy in hit_enemies:
                if enemy.is_alive:
                    destroyed = enemy.take_damage()
                    if destroyed:
                        # Начисление очков уже происходит в методе destroy()
                        pass
        # Обработка бонусов
        if player is not None:
            bonus_hit = pygame.sprite.spritecollide(player, bonus_group, True)
            for bonus in bonus_hit:
                # За взятие любого бонуса начисляем 500 очков

                global_score += 500

                # Обработка бонуса в зависимости от его типа
                if bonus.type == "armor":
                    # Включаем щит на 10 секунд (сбрасываем флаг бесконечного щита)
                    player.shield_active = True
                    player.shield_start = pygame.time.get_ticks()
                    shield_end_time = pygame.time.get_ticks() + 10000  # 10 секунд
                    player.shield_unlimited = False
                    bonus_channel.play(bonus_take_sound)
                    ### ИЗМЕНЕНИЕ: инициализируем armor_rumble_next
                    armor_rumble_next = pygame.time.get_ticks() + 1000
                elif bonus.type == "time_stop":
                    # Останавливаем движение и стрельбу врагов на 10 секунд
                    enemy_stop = True
                    enemy_stop_end_time = pygame.time.get_ticks() + 10000
                    bonus_channel.play(bonus_take_sound)
                    ### ИЗМЕНЕНИЕ: инициализируем "следующую пульсацию" через 1 секунду
                    time_stop_rumble_next = pygame.time.get_ticks() + 1000
                elif bonus.type == "hq_boost":
                    activate_hq_boost()
                    bonus_channel.play(bonus_take_sound)
                elif bonus.type == "tank_boost":
                    ### ИЗМЕНЕНИЕ:
                    # Увеличиваем глобальный уровень прокачки, но не выше 4
                    player_upgrade_level = min(4, player_upgrade_level + 1)
                    # Если игрок жив, сразу обновляем его параметры
                    if player is not None:
                        player.set_upgrade_level(player_upgrade_level)
                    bonus_channel.play(bonus_take_sound)
                elif bonus.type == "grenade":
                    # Взрываем все вражеские танки (без начисления дополнительных очков)
                    for enemy in list(enemies):
                        enemy.destroy(no_score=True)
                    # Чуть сильнее, чем при убийстве одного танка
                    do_rumble(0.7, 0.7, 300)
                    bonus_channel.play(bonus_take_sound)
                elif bonus.type == "life":
                    # Добавляем одну жизнь игроку
                    player_lives += 1
                    bonus_channel.play(bonus_life_sound)
                
                # Создаём всплывающий спрайт с 500 очками
                score_popup = ScorePopup(bonus.rect.center, 500)
                popups.add(score_popup)
        # Если игрок сталкивается с пулями врагов и защитное поле не активно – уничтожаем игрока
        if player is not None:
            player_hits = pygame.sprite.spritecollide(player, enemy_bullets, True)
            if player_hits and (not hasattr(player, "shield_active") or not player.shield_active):
                # Для каждой пули, попавшей в игрока
                for bullet in player_hits:
                    create_hit_explosion(bullet.rect.center)
                do_rumble(1.0, 1.0, 700)
                player.destroy()
                player_respawn_time = now + 3000
                player = None
                player_sound_channel.stop()
                current_player_sound = None
                player_lives -= 1
                ### ИЗМЕНЕНИЕ: сброс уровня прокачки на 1
                player_upgrade_level = 1
                if player_lives <= 0:
                    start_game_over_sequence()

        # Создание танка игрока
        if player is None and now >= player_respawn_time and not game_over:
            spawn_anim = SpawnAnimation(player_spawn_point, spawn_player_callback)
            spawn_group.add(spawn_anim)
            all_sprites.add(spawn_anim)
            player_respawn_time = float('inf')

        if player is not None and hasattr(player, "shield_active") and player.shield_active:
            if not player.shield_unlimited and now >= shield_end_time:
                player.shield_active = False
            else:
                # Анимация щита
                elapsed_shield = now - player.shield_start
                shield_frame = (elapsed_shield // 20) % 2
                game_surface.blit(shield_sprites[shield_frame], player.rect.topleft)
                if not player.shield_unlimited:
                    if now >= armor_rumble_next:
                        do_rumble(0.0, 0.2, 150)
                        armor_rumble_next = now + 1000

        if player is not None:
            if player.is_moving:
                if current_player_sound != "drive":
                    player_sound_channel.stop()
                    player_sound_channel.play(drive_sound, loops=-1)
                    current_player_sound = "drive"
            else:
                # Если игрок не двигается, в _animate() уже запускается stand звук
                pass
        # Объединяем все пули в одну группу
        all_bullets = pygame.sprite.Group()
        all_bullets.add(player_bullets, enemy_bullets)
        # Проверяем попадания в штаб
        for hq in all_sprites:
            if isinstance(hq, Headquarters) and not hq.destroyed:
                if pygame.sprite.spritecollideany(hq, all_bullets):
                    do_rumble(1.0, 1.0, 1000)
                    hq.destroy()
                    break

        if hq_boost_active:
            time_left = hq_boost_end_time - pygame.time.get_ticks()
            
            # Мигание в последние 5 секунд
            if time_left <= 5000:
                if pygame.time.get_ticks() - last_blink > 500:
                    blink_state = not blink_state
                    last_blink = pygame.time.get_ticks()
                    
                    # Меняем спрайты стен
                    for wall in hq_temp_walls:
                        if blink_state:
                            # Показываем кирпичные стены
                            wall.image = BrickWall(wall.rect.x, wall.rect.y, wall.active_cells).image
                        else:
                            # Показываем бетонные стены
                            wall.image = ConcreteWall(wall.rect.x, wall.rect.y, wall.active_cells).image
            
            # Завершение бонуса
            if time_left <= 0:
                deactivate_hq_boost()

        game_surface.fill((117, 117, 117))
        pygame.draw.rect(game_surface, (0, 0, 0), FIELD_RECT)
        if show_grid:
            for x in range(FIELD_RECT.left, FIELD_RECT.right + 1, CELL_SIZE):
                pygame.draw.line(game_surface, (50, 50, 50), (x, FIELD_RECT.top), (x, FIELD_RECT.bottom))
            for y in range(FIELD_RECT.top, FIELD_RECT.bottom + 1, CELL_SIZE):
                pygame.draw.line(game_surface, (50, 50, 50), (FIELD_RECT.left, y), (FIELD_RECT.right, y))
        all_sprites.draw(game_surface)
        for obstacle in obstacles:
            if isinstance(obstacle, BrickWall):
                obstacle.draw(game_surface)
            elif isinstance(obstacle, Water):
                obstacle.update()
        if player is not None and hasattr(player, "shield_active") and player.shield_active:
            elapsed_shield = pygame.time.get_ticks() - player.shield_start
            shield_frame = (elapsed_shield // 20) % 2
            game_surface.blit(shield_sprites[shield_frame], player.rect.topleft)
        popups.draw(game_surface)

        # РИСУЕМ ЛЕС *ПОВЕРХ* ВСЕГО
        forests.draw(game_surface)
        # А ТЕПЕРЬ БОНУСЫ
        bonus_group.draw(game_surface)

        # Отрисовка Game Over поверх всего
        if game_over and game_over_sprite is not None:
            game_surface.blit(game_over_sprite.image, game_over_sprite.rect)
        
        screen.fill((0, 0, 0))
        screen.blit(game_surface, (0, 0))
        # Рисуем на боковой панели (относительно окна) сетку оставшихся врагов
        for i, (cell_x, cell_y) in enumerate(grid_cells):
            pos_on_screen = ((GAME_WIDTH - 64) + cell_x, cell_y)
            if grid_status[i]:
                screen.blit(present_sprite, pos_on_screen)
            else:
                screen.blit(absent_sprite, pos_on_screen)
        # Иконка для жизней (32x32)
        screen.blit(life_icon_sprite, (497, 272))
        # Число жизней (рассчитываем как lives-1)
        current_lives = max(0, player_lives - 1)
        if current_lives in number_sprites:
            screen.blit(number_sprites[current_lives], (512, 288))
        else:
            screen.blit(number_sprites[0], (512, 288))  # fallback
        screen.blit(level_icon_sprite, (496, 368))  # Иконка уровня
        level_digits = render_level_number(current_level)
        if len(level_digits) == 1:
            # Если одна цифра (уровень 1..9), рисуем в x=512
            screen.blit(level_digits[0], (512, 400))
        elif len(level_digits) == 2:
            # Если две цифры (уровень 10..99), десятки в x=496, единицы в x=512
            screen.blit(level_digits[0], (496, 400))
            screen.blit(level_digits[1], (512, 400))
        # Счет
        score_digits = render_number(global_score)
        score_x = WINDOW_WIDTH // 2 - (len(score_digits) * 8)  # Центрирование
        score_y = TOP_MARGIN // 2 - 8
        for i, digit in enumerate(score_digits):
            screen.blit(digit, (score_x + i*16, score_y))
        if global_score >= 20000 and not score_life_20000_awarded:
            player_lives += 1
            bonus_channel.play(bonus_life_sound)  # проигрываем звук bonus_life.ogg
            score_life_20000_awarded = True

        if global_score >= 100000 and not score_life_100000_awarded:
            player_lives += 1
            bonus_channel.play(bonus_life_sound)  # проигрываем звук bonus_life.ogg
            score_life_100000_awarded = True    
        # Если уровень окончен (все 20 врагов убиты)
        if enemies_remaining_level <= 0 and enemies_to_spawn <= 0 and len(enemies) <= 0 and len(spawn_group) <= 0:
            if level_complete_time is None:
                level_complete_time = now

            ### ИЗМЕНЕНИЕ: останавливаем "stand" или любой звук игрока
            player_sound_channel.stop()
            current_player_sound = None

            if now - level_complete_time >= 3000:
                next_level()
        # Очищаем замороженный кадр, если он был использован ранее
        paused_frame = None

        # Отображение прямоугольников вокруг объектов
        if show_masks:
            for obstacle in obstacles:
                pygame.draw.rect(screen, (255, 255, 0), obstacle.rect, 1)

        # Отображение путей танков врагов
        if show_paths:
            for enemy in enemies:
                if enemy.path:
                    print(f"Enemy {enemy} path: {enemy.path}")
                    for i in range(len(enemy.path) - 1):
                        pygame.draw.line(screen, enemy.path_color, enemy.path[i], enemy.path[i + 1], 2)
    else:
        # Режим паузы: игра не обновляется, отображается предыдущий кадр с наложением мигающей надписи PAUSE
        now = pygame.time.get_ticks()
        if now - last_blink_time > 500:
            pause_blink = not pause_blink
            last_blink_time = now
        if paused_frame is None:
            paused_frame = screen.copy()
        screen.blit(paused_frame, (0, 0))
        # Отображаем спрайт паузы по центру игровой области (FIELD_RECT)
        if pause_blink:
            pause_x = FIELD_RECT.left + (FIELD_RECT.width - pause_sprite.get_width()) // 2
            pause_y = FIELD_RECT.top + (FIELD_RECT.height - pause_sprite.get_height()) // 2
            screen.blit(pause_sprite, (pause_x, pause_y))
    if game_over:
        if game_over_phase == 0:
            game_over_sprite.update()
            if game_over_sprite.arrived:
                game_over_phase = 1
                game_over_start_time = pygame.time.get_ticks()
        elif game_over_phase == 1:
            if pygame.time.get_ticks() - game_over_start_time >= 3000:
                game_over_phase = 2
        elif game_over_phase == 2:
            # Уничтожаем игрока только на этой стадии
            if player is not None:
                player.kill()
                player = None
                
            # Очистка ресурсов и возврат в меню
            all_sprites.empty()
            tank_group.empty()
            enemies.empty()
            spawn_group.empty()
            explosions.empty()
            player_bullets.empty()
            enemy_bullets.empty()
            bonus_group.empty()
            pygame.mixer.stop()
            
            # Полный сброс глобальных переменных
            player = None
            current_level = 1
            enemies_to_spawn = 20
            enemies_remaining_level = 20
            
            # Перезапуск игры
            mode = main_menu()
            reset_grid()
            game_over = False
            game_over_phase = 0
            game_over_sprite = None
            player_lives = 3
            level_transition(current_level)
            player_respawn_time = pygame.time.get_ticks()
    pygame.display.flip()
    clock.tick(60)