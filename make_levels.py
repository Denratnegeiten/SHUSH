import json
import os

def create_levels():
    os.makedirs('assets/levels', exist_ok=True)

    # Используем твои базовые текстуры
    tiles = {
        "0": "street_floor_96x64.png",
        "1": "home_floor_96x64.png",
        "2": "walls_96x64.png"
    }
    
    # Используем твои модельки (игра по словам в названии поймет, что это)
    sprites = {
        "spr_vase": "vase_table_76x42.png",
        "spr_pic": "picture90_26x56_1.png",
        "spr_sofa": "sofa_60x36.png",
        "spr_bush": "bush_36x60.png"
    }

    def make_empty_map():
        return [[0 for _ in range(100)] for _ in range(100)]

    def draw_box(m, x1, y1, x2, y2, floor_id=1, wall_id=2):
        for r in range(y1, y2+1):
            for c in range(x1, x2+1):
                if r == y1 or r == y2 or c == x1 or c == x2:
                    m[r][c] = wall_id
                else:
                    m[r][c] = floor_id
        # Прорубаем "дверь" снизу
        m[y2][(x1+x2)//2] = floor_id
        m[y2][(x1+x2)//2 + 1] = floor_id

    # ==========================================
    # УРОВЕНЬ 1: Дом (Обучение)
    m1 = make_empty_map()
    draw_box(m1, 10, 10, 20, 20)
    lvl1 = {
        "entrance_pos": [15*64, 23*64], # Спавн на улице перед дверью
        "tiles": tiles, "sprites": sprites, "map": m1,
        "objects": [
            {"name": "obj_1", "sprite_id": "spr_sofa", "pos": [15*64, 15*64]},
            {"name": "obj_2", "sprite_id": "spr_pic", "pos": [15*64, 11*64]},
            {"name": "obj_3", "sprite_id": "spr_vase", "pos": [12*64, 18*64]}
        ],
        "guards_data": [{"type": "normal", "x": 15*64, "y": 17*64}]
    }

    # ==========================================
    # УРОВЕНЬ 2: Выставка (Быстрые враги)
    m2 = make_empty_map()
    draw_box(m2, 5, 5, 30, 25)
    # Добавляем стены-перегородки
    for r in range(10, 20): m2[r][12] = 2; m2[r][22] = 2
    lvl2 = {
        "entrance_pos": [17*64, 28*64],
        "tiles": tiles, "sprites": sprites, "map": m2,
        "objects": [
            {"name": "obj_1", "sprite_id": "spr_bush", "pos": [10*64, 10*64]},
            {"name": "obj_2", "sprite_id": "spr_bush", "pos": [25*64, 15*64]},
            {"name": "obj_3", "sprite_id": "spr_pic", "pos": [13*64, 15*64]},
            {"name": "obj_4", "sprite_id": "spr_pic", "pos": [23*64, 10*64]}
        ],
        "guards_data": [
            {"type": "fast", "x": 17*64, "y": 10*64},
            {"type": "fast", "x": 17*64, "y": 20*64}
        ]
    }

    # ==========================================
    # УРОВЕНЬ 3: Лабиринт (Сложный)
    m3 = make_empty_map()
    draw_box(m3, 5, 5, 25, 25)
    # Стены лабиринта
    for c in range(5, 20): m3[10][c] = 2; m3[15][c+5] = 2; m3[20][c] = 2
    lvl3 = {
        "entrance_pos": [6*64, 28*64],
        "tiles": tiles, "sprites": sprites, "map": m3,
        "objects": [
            {"name": "obj_1", "sprite_id": "spr_pic", "pos": [6*64, 6*64]},
            {"name": "obj_2", "sprite_id": "spr_vase", "pos": [23*64, 11*64]},
            {"name": "obj_3", "sprite_id": "spr_sofa", "pos": [6*64, 16*64]}
        ],
        "guards_data": [
            {"type": "random", "x": 15*64, "y": 8*64},
            {"type": "random", "x": 10*64, "y": 18*64}
        ]
    }

    # ==========================================
    # УРОВЕНЬ 4: Хранилище (Хардкор с Тайзерами)
    m4 = make_empty_map()
    # Длинный коридор
    for r in range(20, 30):
        m4[r][14] = 2; m4[r][17] = 2
        m4[r][15] = 1; m4[r][16] = 1
    # Зал-хранилище
    draw_box(m4, 10, 5, 21, 19)
    m4[19][15] = 1; m4[19][16] = 1 # Открываем вход
    lvl4 = {
        "entrance_pos": [15*64, 32*64],
        "tiles": tiles, "sprites": sprites, "map": m4,
        "objects": [
            {"name": "obj_1", "sprite_id": "spr_pic", "pos": [12*64, 6*64]},
            {"name": "obj_2", "sprite_id": "spr_vase", "pos": [19*64, 6*64]},
            {"name": "obj_3", "sprite_id": "spr_pic", "pos": [12*64, 10*64]},
            {"name": "obj_4", "sprite_id": "spr_vase", "pos": [19*64, 10*64]},
            {"name": "obj_5", "sprite_id": "spr_sofa", "pos": [15*64, 25*64]} # Укрытие в коридоре
        ],
        "guards_data": [
            {"type": "taser", "x": 15*64, "y": 10*64}, # Стрелки в зале
            {"type": "taser", "x": 15*64, "y": 15*64},
            {"type": "normal", "x": 15*64, "y": 25*64} # Патрульный в коридоре
        ]
    }

    levels = [lvl1, lvl2, lvl3, lvl4]
    for i, lvl in enumerate(levels):
        with open(f"assets/levels/level_{i+1}.json", "w") as f:
            json.dump(lvl, f, indent=2)
        print(f"✅ Уровень {i+1} успешно создан!")

if __name__ == "__main__":
    create_levels()