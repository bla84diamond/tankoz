import pygame
import sys
import random
from datetime import datetime

pygame.init()
pygame.joystick.init()
joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

# =========================
# Параметры отладки
# =========================
show_grid = True        # Видимость сетки

# =========================
# Глобальные переменные
# =========================
global_score = 0  # Добавлено для хранения очков
bonus_active = False  # Флаг активного бонуса
bonus_pos = (0, 0)  # Позиция бонуса
bonus_blink = False  # Состояние мерцания бонуса
last_bonus_blink = 0  # Время последнего мерцания
enemy_counter = 0  # Счетчик появившихся врагов
# Глобальные переменные для бонусов и эффекта остановки времени
enemy_stop = False
enemy_stop_end_time = 0
score_life_20000_awarded = False
score_life_100000_awarded = False

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
pygame.display.set_caption("Боевые танки")

# Поверхности для игры и отладки
game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))

# Загрузка шрифтов
debug_font = pygame.font.SysFont("consolas", 14)
header_font = pygame.font.SysFont("consolas", 16, bold=True)

# Загрузка спрайтов
spritesheet = pygame.image.load("sprites.png").convert_alpha()

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

# Спрайты для танков игрока и врагов
player_sprites = {
    "up": [get_sprite(0, 0, 32, 32), get_sprite(32, 0, 32, 32)],
    "left": [get_sprite(64, 0, 32, 32), get_sprite(96, 0, 32, 32)],
    "down": [get_sprite(128, 0, 32, 32), get_sprite(160, 0, 32, 32)],
    "right": [get_sprite(192, 0, 32, 32), get_sprite(224, 0, 32, 32)]
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
bonus_channel = pygame.mixer.Channel(1)  # Отдельный канал для бонусов
current_player_sound = None  # звук "stand" не запускается, пока игрок не двигается

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

# =========================
# Класс отобрвжения очков
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
        # Выбираем бонус с использованием random.choices по весам
        self.bonus_data = random.choices(bonus_definitions, weights=[bd["weight"] for bd in bonus_definitions])[0]
        self.type = self.bonus_data["type"]
        self.image = self.bonus_data["sprite"]
        self.rect = self.image.get_rect(center=pos)
        self.spawn_time = pygame.time.get_ticks()
        all_sprites.add(self)
        bonus_group.add(self)
        bonus_channel.play(bonus_appear_sound)

    def update(self):
        # Удаляем бонус через 10 секунд
        if pygame.time.get_ticks() - self.spawn_time > 10000:
            self.kill()

# =========================
# Класс для взрыва при попадании
# =========================
class HitExplosion(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        # Можно оставить разброс ±3 пикс., как было, чтобы "вспышка" выглядела рандомно
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
        self.total_duration = 500  # длительность анимации взрыва
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
    def __init__(self, x, y, is_player=True, enemy_type=None):
        super().__init__()
        self.is_player = is_player
        if is_player:
            self.sprites = player_sprites  # Для игрока можно использовать общий словарь
            self.bullet_speed = 10
        else:
            if enemy_type is None:
                enemy_type = 1
            # Создаем копии спрайтов для данного врага, чтобы изменения не влияли на глобальные спрайты
            self.sprites = {
                direction: [frame.copy() for frame in frames]
                for direction, frames in enemy_sprites[enemy_type].items()
            }
        self.current_sprite = 0
        self.last_update = pygame.time.get_ticks()
        self.animation_interval = 500
        self.direction = "up"  # начальное направление
        self.image = self.sprites[self.direction][self.current_sprite]
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 3
        self.shoot_cooldown = 0
        self.is_alive = True
        self.is_moving = False
        self.last_key = None
        self.shield_unlimited = False  # для бесконечного щита
    
    def ai_update(self):
        """Базовый метод для ИИ управления (пустая реализация)"""
        pass
    def update(self, input_keys):
        if self.is_alive and self.is_player:
            old_rect = self.rect.copy()
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

            # Движение
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

            # Ограничение движения в пределах игровой зоны
            self.rect.clamp_ip(FIELD_RECT)
            
            # Базовая проверка коллизий с другими танками
            for tank in tank_group:
                if tank != self and self.rect.colliderect(tank.rect):
                    self.rect = old_rect
                    break

            self.is_moving = (old_rect.x != self.rect.x or old_rect.y != self.rect.y)
            self._animate()

    def _animate(self):
        global current_player_sound  # перемещено в начало функции
        now = pygame.time.get_ticks()
        if self.is_moving:
            if now - self.last_update > self.animation_interval:
                self.last_update = now
                self.current_sprite = (self.current_sprite + 1) % 2
        else:
            # Если игрок не движется, запускаем звук stand (если ещё не играет)
            if self.is_player:
                if current_player_sound != "stand":
                    player_sound_channel.stop()
                    player_sound_channel.play(stand_sound, loops=-1)
                    current_player_sound = "stand"
            self.current_sprite = 0
        self.image = self.sprites[self.direction][self.current_sprite]

    def shoot(self):
        """Стрельба (общий метод)."""
        if self.shoot_cooldown < pygame.time.get_ticks() and self.is_alive:
            # Общие вычисления начальной позиции пули
            if self.direction == "up":
                bullet_x = self.rect.centerx
                bullet_y = self.rect.top - 4
            elif self.direction == "down":
                bullet_x = self.rect.centerx
                bullet_y = self.rect.bottom + 4
            elif self.direction == "left":
                bullet_x = self.rect.left - 4
                bullet_y = self.rect.centery
            else:  # self.direction == "right"
                bullet_x = self.rect.right + 4
                bullet_y = self.rect.centery

            if self.is_player:
                # Если это игрок
                bullet = Bullet(
                    bullet_x,
                    bullet_y,
                    self.direction,
                    owner="player",
                    speed=self.bullet_speed  # у Tank задано self.bullet_speed=10
                )
                player_bullets.add(bullet)
            else:
                # Если это враг
                bullet = Bullet(
                    bullet_x,
                    bullet_y,
                    self.direction,
                    owner="enemy",
                    speed=self.bullet_speed
                )
                enemy_bullets.add(bullet)

            all_sprites.add(bullet)
            self.shoot_cooldown = pygame.time.get_ticks() + 500


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
        # Передаем enemy_type в базовый класс
        super().__init__(x, y, is_player=False, enemy_type=enemy_type)
        global enemy_counter
        enemy_counter += 1
        self.change_direction_time = pygame.time.get_ticks() + random.randint(1000, 5000)
        self.speed = 2  # базовая скорость для врагов
        self.direction = initial_direction
        self.spawn_time = datetime.now().strftime("%H:%M:%S")
        self.destroy_time = None
        self.enemy_type = enemy_type
        self.armor_level = armor_level
        # Если танк тяжелый, можно менять его параметры и цвет:
        if enemy_type == 4:
            self.max_health = armor_level + 1
            self.health = self.max_health
            self._update_color()  # обновляем цвет брони
        self.image = self.sprites[self.direction][self.current_sprite]
        self.rect = self.image.get_rect(center=self.rect.center)
        
        # Настройка характеристик
        if enemy_type == 1:  # Обычный танк
            self.speed = 2
            self.bullet_speed = 8
            self.score_value = 100
        elif enemy_type == 2:  # Бронетранспортёр
            self.speed = 4
            self.bullet_speed = 6
            self.score_value = 200
        elif enemy_type == 3:  # Скорострельный танк
            self.speed = 1
            self.bullet_speed = 21
            self.score_value = 300
        elif enemy_type == 4:  # Тяжелый танк
            self.speed = 1
            self.bullet_speed = 6
            self.armor_level = armor_level
            self.max_health = armor_level + 1
            self.health = self.max_health
            self.score_value = 400
            self._update_color()
        
        # Мерцание для определенных танков
        self.is_special = enemy_counter in [4, 11, 18]
        self.blink_state = False
        self.last_blink = 0
    
    def _update_color(self):
        if self.enemy_type == 4:
            # Получаем список цветов для этого armor_level
            if self.armor_level not in ARMOR_COLORS:
                return  # или вернуть белый цвет по умолчанию
            
            colors_list = ARMOR_COLORS[self.armor_level]
            
            # Индекс в зависимости от (max_health - current_health)
            index = self.max_health - self.health
            if index < 0: index = 0
            if index >= len(colors_list):
                index = len(colors_list) - 1  # защита
            color = colors_list[index]

            # Для всех направлений заново берем "базовые" кадры и перекрашиваем один раз
            for direction in ["up", "down", "left", "right"]:
                new_frames = []
                base_frames = heavy_tank_base_sprites[direction]  # берём «чистые»
                for bf in base_frames:
                    frame_copy = bf.copy()
                    # Накладываем выбранный цвет
                    frame_copy.fill(color, special_flags=pygame.BLEND_RGB_MULT)
                    new_frames.append(frame_copy)
                # Обновляем в self.sprites
                self.sprites[direction] = new_frames

            # Устанавливаем текущую картинку заново (чтобы мгновенно изменился цвет)
            self.image = self.sprites[self.direction][self.current_sprite]
    
    def take_damage(self):
        global bonus_active
        if self.enemy_type == 4:
            self.health -= 1
            # Спавн бонуса при первом попадании в специальный танк
            if self.is_special and self.health == self.max_health - 1:
                cols = GRID_COLS - 2
                rows = GRID_ROWS - 2
                rand_col = random.randint(1, cols)
                rand_row = random.randint(1, rows)
                bonus_x = LEFT_MARGIN + (rand_col * CELL_SIZE) - CELL_SIZE//2
                bonus_y = TOP_MARGIN + (rand_row * CELL_SIZE) - CELL_SIZE//2
                bonus = Bonus((bonus_x, bonus_y))
                bonus_active = True
                self.is_special = False  # <--- ВАЖНО

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

        # Если no_score == True, не показываем всплывающий спрайт очков
        if no_score:
            explosion = Explosion(self.rect.center, score_points=None, popup_duration=250)
        else:
            explosion = Explosion(self.rect.center, score_points=self.score_value, popup_duration=250)
        explosions.add(explosion)
        all_sprites.add(explosion)

        if not no_score:
            global_score += self.score_value

        global enemies_remaining_level
        enemies_remaining_level -= 1

        # Если «специальный» танк – спавним бонус (без изменений)
        if self.is_special and self.enemy_type != 4:
            cols = GRID_COLS - 2
            rows = GRID_ROWS - 2
            rand_col = random.randint(1, cols)
            rand_row = random.randint(1, rows)
            bonus_x = LEFT_MARGIN + (rand_col * CELL_SIZE) - CELL_SIZE // 2
            bonus_y = TOP_MARGIN + (rand_row * CELL_SIZE) - CELL_SIZE // 2
            Bonus((bonus_x, bonus_y))
            bonus_active = True

    def ai_update(self):
        global enemy_stop, enemy_stop_end_time
        if enemy_stop:
            # Если время остановки еще не истекло, пропускаем обновление для этого врага
            if pygame.time.get_ticks() < enemy_stop_end_time:
                return
            else:
                enemy_stop = False  # Сброс эффекта после истечения времени

        # Обновление направления и движения
        old_rect = self.rect.copy()
        now = pygame.time.get_ticks()
        if now >= self.change_direction_time:
            self.direction = random.choice(["up", "down", "left", "right"])
            self.change_direction_time = now + random.randint(1000, 5000)
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
            self.direction = random.choice(["up", "down", "left", "right"])
        for tank in tank_group:
            if tank != self and self.rect.colliderect(tank.rect):
                self.rect = old_rect
                self.direction = random.choice(["up", "down", "left", "right"])
                break
        self.rect.clamp_ip(FIELD_RECT)

        # Выполняем анимацию (обновляет self.current_sprite и self.image)
        self._animate()

        # Если танк специальный (бонусный), переключаем спрайт с использованием бонусных спрайтов
        if self.is_special and self.is_alive:
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

    def shoot(self):
        if self.shoot_cooldown < pygame.time.get_ticks() and self.is_alive:
            if self.direction == "up":
                bullet_x = self.rect.centerx
                bullet_y = self.rect.top - 4
            elif self.direction == "down":
                bullet_x = self.rect.centerx
                bullet_y = self.rect.bottom + 4
            elif self.direction == "left":
                bullet_x = self.rect.left - 4
                bullet_y = self.rect.centery
            elif self.direction == "right":
                bullet_x = self.rect.right + 4
                bullet_y = self.rect.centery
            bullet = Bullet(bullet_x, bullet_y, self.direction, owner="enemy")
            enemy_bullets.add(bullet)
            all_sprites.add(bullet)
            self.shoot_cooldown = pygame.time.get_ticks() + 500

# =========================
# Класс Bullet – пуля
# =========================
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner, speed=10):
        super().__init__()
        self.image = bullet_sprites[direction]
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed  # Добавлен параметр скорости
        self.direction = direction
        self.owner = owner

    def update(self):
        old_pos = self.rect.center
        if self.direction == "up":
            self.rect.y -= self.speed
        elif self.direction == "down":
            self.rect.y += self.speed
        elif self.direction == "left":
            self.rect.x -= self.speed
        elif self.direction == "right":
            self.rect.x += self.speed
        
        # Проверка столкновения с границами игрового поля
        if not FIELD_RECT.collidepoint(self.rect.center):
            # Исправление: звук от столкновения со стеной проигрываем ТОЛЬКО если пуля принадлежит игроку
            if self.owner == "player":
                wall_sound.play()
            explosion = HitExplosion(old_pos)
            explosions.add(explosion)
            all_sprites.add(explosion)
            self.kill()

# =========================
# Класс для спрайта завершения игры
# =========================
class GameOverSprite(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = get_sprite(576, 367, 64, 32)
        self.rect = self.image.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT + 32))
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
    global game_over, game_over_sprite, game_over_phase, player_lives, player
    game_over = True
    game_over_phase = 0
    game_over_sprite = GameOverSprite()
    all_sprites.add(game_over_sprite)
    
    # Полный сброс состояния игрока
    if player is not None:
        player.kill()
    player = None
    player_respawn_time = float('inf')

# =========================
# Глобальные переменные уровня
# =========================
current_level = 1
enemies_to_spawn = 20  # сколько ещё врагов предстоит появиться (из 20)
enemies_remaining_level = 20  # сколько врагов осталось убить в этом уровне
player_lives = 3
game_over = False
game_over_phase = 0  # 0 - движение спрайта, 1 - ожидание, 2 - переход в меню
game_over_sprite = None

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
    enemy_counter = 0
    reset_grid()
    # Удаляем все оставшиеся вражеские спрайты, если таковые остались
    for enemy in list(enemies):
        enemy.kill()
    # Сбрасываем время респауна игрока, чтобы условие в основном цикле сработало
    player_respawn_time = pygame.time.get_ticks()

def spawn_player_callback(pos):
    global player, shield_end_time
    now = pygame.time.get_ticks()
    player = Tank(pos[0], pos[1], is_player=True)
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
    if enemies_to_spawn > 15:  # Первые 5 танков
        enemy_type = random.choice([1, 2, 3])
    elif enemies_to_spawn > 10:
        enemy_type = random.choice([1, 2, 3, 4])
    else:
        enemy_type = 4 if random.random() < 0.3 else random.choice([1, 2, 3])
    
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

    enemies_to_spawn -= 1
    update_grid_after_spawn()
    spawn_occupancy[pos] = False

# =========================
# Функция перехода на уровень (экран STAGE)
# =========================
def level_transition(level):
    start_sound.play()
    if level > 1:
        final_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        final_surface.fill((99, 99, 99))  # затемнённые отступы
        pygame.draw.rect(final_surface, (0, 0, 0), FIELD_RECT)

    # 0. Очистка всех спрайтов
    global all_sprites, tank_group, enemies, spawn_group, explosions, player_bullets, enemy_bullets
    all_sprites.empty()
    tank_group.empty()
    enemies.empty()
    spawn_group.empty()
    explosions.empty()
    player_bullets.empty()
    enemy_bullets.empty()

    #
    # --- Сокращение анимации закрытия до 600 мс (было 1200) ---
    #
    anim_duration = 600
    start_anim = pygame.time.get_ticks()
    
    while True:
        now = pygame.time.get_ticks()
        elapsed = now - start_anim
        if elapsed > anim_duration:
            break
            
        ratio = elapsed / anim_duration
        fill_height = int((WINDOW_HEIGHT // 2) * ratio)
        
        screen.fill((0, 0, 0))
        pygame.draw.rect(screen, (99, 99, 99), (0, 0, WINDOW_WIDTH, fill_height))
        pygame.draw.rect(
            screen, (99, 99, 99),
            (0, WINDOW_HEIGHT - fill_height, WINDOW_WIDTH, fill_height)
        )
        
        pygame.display.flip()
        pygame.time.delay(16)

    # 1. Рисуем надпись STAGE + номер уровня на центре игрового поля
    level_digits = render_level_number(level)
    total_width = 80 + 16 + (16 * len(level_digits))  # 80 — ширина спрайта "STAGE", небольшой зазор + цифры
    start_x = FIELD_RECT.left + (FIELD_RECT.width - total_width) // 2
    start_y = FIELD_RECT.top + (FIELD_RECT.height - 14) // 2
    
    stage_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    stage_surface.fill((99, 99, 99))
    stage_surface.blit(stage_text_sprite, (start_x, start_y))

    #
    # --- Для выравнивания по центру спрайта "STAGE":
    #     Спрайт "STAGE" высотой 14 px, цифры – 16 px, поэтому сместим их на -1 по вертикали
    #
    digit_x = start_x + 80  # справа от "STAGE"
    digit_y = start_y - 1   # чуть выше для центрирования
    for digit_sprite in level_digits:
        digit_x += 16
        stage_surface.blit(digit_sprite, (digit_x, digit_y))
    
    screen.blit(stage_surface, (0, 0))
    pygame.display.flip()

    # Ждём завершения звука
    while pygame.mixer.get_busy():
        pygame.time.wait(50)

    #
    # --- Ускоряем раскрытие экрана в 2 раза (1000 → 500) ---
    #
    anim_duration = 500
    start_anim = pygame.time.get_ticks()

    # Готовим финальный кадр
    mask_surface = pygame.Surface((FIELD_RECT.size), pygame.SRCALPHA)
    final_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    final_surface.fill((99, 99, 99))
    pygame.draw.rect(final_surface, (0, 0, 0), FIELD_RECT)

    while True:
        now = pygame.time.get_ticks()
        elapsed = now - start_anim
        if elapsed > anim_duration:
            break

        ratio = elapsed / anim_duration
        current_height = int((FIELD_RECT.height // 2) * (1 - ratio))

        mask_surface.fill((99, 99, 99))
        pygame.draw.rect(
            mask_surface, (0, 0, 0, 0),
            (0, current_height, FIELD_RECT.width, FIELD_RECT.height - 2 * current_height)
        )

        screen.blit(final_surface, (0, 0))
        screen.blit(mask_surface, FIELD_RECT.topleft)
        pygame.display.flip()
        pygame.time.delay(16)

    screen.blit(final_surface, (0, 0))
    pygame.display.flip()

# =========================
# Главное меню выбора режима (исправлено управление джойстиком)
# =========================
def main_menu():
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
    indicator_sprite = player_sprites["right"][0]
    indicator_rect = indicator_sprite.get_rect()
    clock = pygame.time.Clock()
    selected_mode = None
    joystick_debounce = 0  # Защита от двойного срабатывания

    while selected_mode is None:
        now = pygame.time.get_ticks()
        dt = now - menu_start_time
        if dt >= 1000:
            t = dt - 1000
            if t < slide_duration:
                menu_y = WINDOW_HEIGHT - ((WINDOW_HEIGHT - final_menu_y) * (t / slide_duration))
            else:
                menu_y = final_menu_y

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
            if event.type == pygame.JOYHATMOTION:
                if now >= menu_start_time + 1000 + slide_duration and now - joystick_debounce > 200:
                    if event.value[1] == 1:  # Вверх
                        selection_index = (selection_index - 1) % len(option_texts)
                        joystick_debounce = now
                    elif event.value[1] == -1:  # Вниз
                        selection_index = (selection_index + 1) % len(option_texts)
                        joystick_debounce = now
                        
            if event.type == pygame.JOYBUTTONDOWN:
                if now >= menu_start_time + 1000 + slide_duration:
                    selected_mode = selection_index

        menu_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        menu_surface.fill((0, 0, 0))
        title_x = (WINDOW_WIDTH - title_rect.width) // 2
        menu_surface.blit(title_text, (title_x, menu_y))
        current_y = menu_y + title_rect.height + spacing
        for i, opt in enumerate(option_texts):
            opt_rect = opt.get_rect()
            opt_x = (WINDOW_WIDTH - opt_rect.width) // 2
            menu_surface.blit(opt, (opt_x, current_y))
            if i == selection_index:
                indicator_rect.midright = (opt_x - 10, current_y + opt_rect.height // 2)
                menu_surface.blit(indicator_sprite, indicator_rect)
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

# Точка появления игрока: 5-я клетка снизу (x=208, y=432)
player_spawn_point = (208, 432)

next_spawn_time = pygame.time.get_ticks() + random.randint(1000, 7000)

# Позиции появления врагов (на верхней строке)
spawn_positions = [
    (LEFT_MARGIN + 0 * CELL_SIZE + 16, TOP_MARGIN + 0 * CELL_SIZE + 16),
    (LEFT_MARGIN + 6 * CELL_SIZE + 16, TOP_MARGIN + 0 * CELL_SIZE + 16),
    (LEFT_MARGIN + 12 * CELL_SIZE + 16, TOP_MARGIN + 0 * CELL_SIZE + 16)
]

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
        if event.type == pygame.JOYHATMOTION:
            # Получаем значение D-pad:
            hat = event.value  # tuple (x, y)
            # Вы можете сохранить его в глобальной переменной, например, joystick_hat = hat
        if event.type == pygame.JOYBUTTONDOWN:
            # Кнопка Start (пауза)
            if event.button == 7:
                paused = not paused
                pause_sound.play()
                if paused:
                    player_sound_channel.stop()
                    current_player_sound = None
                else:
                    current_player_sound = None
                    paused_frame = None
            # Кнопка Back (щит)
            elif event.button == 6 and not paused:  # Select/Back
                if player is not None:
                    player.shield_active = not player.shield_active
                    player.shield_unlimited = True
                    if player.shield_active:
                        player.shield_start = pygame.time.get_ticks()
                        shield_end_time = float('inf')
                    else:
                        shield_end_time = 0
            # Остальные кнопки (только если не пауза)
            elif not paused and player is not None and event.button != 6 and event.button != 7:
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
            next_spawn_time = now + random.randint(1000, 7000)

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
            hat = joystick.get_hat(0)  # Получаем значение D-pad (tuple (x, y))
            if hat[1] == 1:
                input_keys[pygame.K_UP] = True
                input_keys[pygame.K_w] = True
            elif hat[1] == -1:
                input_keys[pygame.K_DOWN] = True
                input_keys[pygame.K_s] = True
            if hat[0] == -1:
                input_keys[pygame.K_LEFT] = True
                input_keys[pygame.K_a] = True
            elif hat[0] == 1:
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

        pygame.sprite.groupcollide(player_bullets, enemy_bullets, True, True)
        hits = pygame.sprite.groupcollide(player_bullets, enemies, True, False)
        for bullet, hit_enemies in hits.items():
            # Новое: создаём короткую вспышку в месте попадания
            explosion = HitExplosion(bullet.rect.center)
            explosions.add(explosion)
            all_sprites.add(explosion)

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
                elif bonus.type == "time_stop":
                    # Останавливаем движение и стрельбу врагов на 10 секунд
                    enemy_stop = True
                    enemy_stop_end_time = pygame.time.get_ticks() + 10000
                    bonus_channel.play(bonus_take_sound)
                elif bonus.type == "hq_boost":
                    # Заглушка для усиления штаба
                    print("Усиление штаба активировано (заглушка)")
                    bonus_channel.play(bonus_take_sound)
                elif bonus.type == "tank_boost":
                    # Заглушка для усиления танка
                    print("Усиление танка активировано (заглушка)")
                    bonus_channel.play(bonus_take_sound)
                elif bonus.type == "grenade":
                    # Взрываем все вражеские танки (без начисления дополнительных очков)
                    for enemy in list(enemies):
                        enemy.destroy(no_score=True)
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
                    explosion = HitExplosion(bullet.rect.center)  # Берём позицию конкретной пули
                    explosions.add(explosion)
                    all_sprites.add(explosion)
                player.destroy()
                player_respawn_time = now + 3000
                player = None
                player_sound_channel.stop()
                current_player_sound = None
                player_lives -= 1
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

        if player is not None:
            if player.is_moving:
                if current_player_sound != "drive":
                    player_sound_channel.stop()
                    player_sound_channel.play(drive_sound, loops=-1)
                    current_player_sound = "drive"
            else:
                # Если игрок не двигается, в _animate() уже запускается stand звук
                pass

        game_surface.fill((99, 99, 99))
        pygame.draw.rect(game_surface, (0, 0, 0), FIELD_RECT)
        if show_grid:
            for x in range(FIELD_RECT.left, FIELD_RECT.right + 1, CELL_SIZE):
                pygame.draw.line(game_surface, (50, 50, 50), (x, FIELD_RECT.top), (x, FIELD_RECT.bottom))
            for y in range(FIELD_RECT.top, FIELD_RECT.bottom + 1, CELL_SIZE):
                pygame.draw.line(game_surface, (50, 50, 50), (FIELD_RECT.left, y), (FIELD_RECT.right, y))
        all_sprites.draw(game_surface)
        if player is not None and hasattr(player, "shield_active") and player.shield_active:
            elapsed_shield = pygame.time.get_ticks() - player.shield_start
            shield_frame = (elapsed_shield // 20) % 2
            game_surface.blit(shield_sprites[shield_frame], player.rect.topleft)
        popups.draw(game_surface)
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
        if enemies_remaining_level <= 0 and enemies_to_spawn == 0 and len(enemies) == 0 and len(spawn_group) == 0:
            if level_complete_time is None:
                level_complete_time = now
            if now - level_complete_time >= 3000:
                next_level()
        # Очищаем замороженный кадр, если он был использован ранее
        paused_frame = None
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
            # Очистка ресурсов и возврат в меню
            all_sprites.empty()
            tank_group.empty()
            enemies.empty()
            spawn_group.empty()
            explosions.empty()
            player_bullets.empty()
            enemy_bullets.empty()
            pygame.mixer.stop()
            
            # Полный сброс глобальных переменных
            #global current_level, enemies_to_spawn, enemies_remaining_level, player
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
