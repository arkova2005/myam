import subprocess
import os
import re
import sqlite3
import random
import sys
import time

# ----------------------------- НАСТРОЙКИ ---------------------------------
FLEX_EXE = r"C:\Program Files\FlexPDE8\FlexPDE8n.exe"   # путь к FlexPDE (консольная версия)
TEMPLATE_PDE = "task2.pde"          # файл-шаблон модели
NUM_POINTS = 16                     # количество контрольных точек
NUM_RUNS = 10000                    # количество прогонов (10 000)
DB_NAME = "anisotropy_results.db"   # файл базы данных

# --- ГЕНЕРАЦИЯ ДОПУСТИМЫХ Aij (A11=1) ---
def generate_random_Aij():
    """
    Возвращает кортеж (A12, A16, A22, A26, A66)
    удовлетворяющий условиям положительной определённости:
    1. A22 > 0
    2. A11*A22 - A12^2 > 0   (A11=1)
    3. det(M) > 0, где M – матрица 3x3.
    """
    while True:
        # Диапазоны – можно подобрать эмпирически
        A12 = random.uniform(-0.9, 0.9)
        A16 = random.uniform(-0.5, 0.5)
        A22 = random.uniform(0.1, 3.0)
        A26 = random.uniform(-0.5, 0.5)
        A66 = random.uniform(0.1, 2.0)

        # Условие 2: 1*A22 - A12^2 > 0
        if A22 - A12*A12 <= 0:
            continue

        # Условие 3: определитель 3x3
        # | A11 A12 A16 |
        # | A12 A22 A26 |
        # | A16 A26 A66 |
        det = (1.0 * A22 * A66 +
               2 * A12 * A16 * A26 -
               1.0 * A26 * A26 -
               A22 * A16 * A16 -
               A66 * A12 * A12)
        if det > 0:
            return A12, A16, A22, A26, A66

# --- ЗАПУСК FLEXPDE И ПОЛУЧЕНИЕ ВЫВОДА ---
def run_flexpde(a12, a16, a22, a26, a66):

    # 1. Подготовка содержимого
    with open(TEMPLATE_PDE, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'A12\s*=\s*[-\d.eE]+', f'A12 = {a12}', content)
    content = re.sub(r'A16\s*=\s*[-\d.eE]+', f'A16 = {a16}', content)
    content = re.sub(r'A22\s*=\s*[-\d.eE]+', f'A22 = {a22}', content)
    content = re.sub(r'A26\s*=\s*[-\d.eE]+', f'A26 = {a26}', content)
    content = re.sub(r'A66\s*=\s*[-\d.eE]+', f'A66 = {a66}', content)

    # 2. Создаём временный .pde файл
    base_name = f"temp_{int(time.time()*1000)}"
    pde_file = base_name + ".pde"
    with open(pde_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # 3. Запуск FlexPDE (ключи -s -a)
    cmd = [FLEX_EXE, '-s', '-a', pde_file]
    try:
        subprocess.run(cmd, capture_output=True, timeout=120)
    except Exception as e:
        print(f"  Ошибка запуска: {e}")
        if os.path.exists(pde_file):
            os.unlink(pde_file)
        return ""

    # 4. Ищем папку с результатами
    output_dir = None
    for _ in range(30):
        dirs = [d for d in os.listdir('.') if d.startswith(base_name) and d.endswith('_output')]
        if dirs:
            output_dir = dirs[0]
            break
        time.sleep(0.5)

    if not output_dir:
        print(f"  Не найдена выходная папка для {pde_file}")
        if os.path.exists(pde_file):
            os.unlink(pde_file)
        return ""

    # 5. Ищем файл summary_output.txt
    summary_path = os.path.join(output_dir, "summary_output.txt")
    if not os.path.exists(summary_path):
        out_files = [f for f in os.listdir(output_dir) if f.endswith('.out')]
        if out_files:
            summary_path = os.path.join(output_dir, out_files[0])
        else:
            print(f"  Не найден файл с результатами в {output_dir}")
            # очистка...
            return ""

    # 6. Читаем результаты
    with open(summary_path, 'r', encoding='utf-8', errors='replace') as f:
        output = f.read()

    # 7. Очистка
    try:
        if os.path.exists(pde_file):
            os.unlink(pde_file)
        for f in os.listdir(output_dir):
            os.unlink(os.path.join(output_dir, f))
        os.rmdir(output_dir)
    except:
        pass

    return output

# --- ПАРСИНГ ВЫВОДА ---
def parse_flexpde_output(output, num_points):
    """
    Извлекает из вывода FlexPDE:
    - A0, A11, A12, A16, A22, A26, A66 (строка 'A = ...')
    - точки P1...Pnum_points (если есть)
    - перемещения u1...unum_points
    - N1, N2
    Возвращает словарь или None при ошибке.
    """
    res = {}
    print("DEBUG: вывод FlexPDE (первые 500 символов):")
    print(repr(output[:500]))
    # 1. Поиск строки с A (формат: "A = 1, 1, 0.8, 0.2, 2, 0.1, 1")
    a_match = re.search(r'A\s*=\s*([^\n]+)', output)
    if not a_match:
        print("Не найдена строка с A")
        return None
    parts = a_match.group(1).split(',')
    if len(parts) != 7:
        print(f"Неверный формат A: ожидалось 7 чисел, получено {len(parts)}")
        return None
    try:
        # Преобразуем в float (float сам убирает пробелы)
        A0, A11, A12, A16, A22, A26, A66 = map(float, parts)
        res.update({'A0': A0, 'A11': A11, 'A12': A12, 'A16': A16,
                    'A22': A22, 'A26': A26, 'A66': A66})
    except ValueError as e:
        print(f"Ошибка преобразования чисел A: {e}")
        return None

    # 2. Координаты точек (если есть)
    points = []
    for i in range(1, num_points+1):
        # Ищем строки типа "P1 = 5.5, 0" или "P1 = 5.5 0"
        p_match = re.search(rf'P{i}\s*=\s*([-\d.eE]+)\s*[, ]?\s*([-\d.eE]+)', output)
        if p_match:
            x = float(p_match.group(1))
            y = float(p_match.group(2))
            points.append((x, y))
        else:
            points.append((None, None))
    res['points'] = points

    # 3. Перемещения (обязательный блок)
    u_values = []
    for i in range(1, num_points+1):
        # Формат: "u1 = 0.012748, 6.187163e-4"
        u_match = re.search(rf'u{i}\s*=\s*([-\d.eE]+)\s*,\s*([-\d.eE]+)', output)
        if u_match:
            ux = float(u_match.group(1))
            uy = float(u_match.group(2))
            u_values.append((ux, uy))
        else:
            # Если хотя бы одно перемещение не найдено, считаем весь прогон неудачным
            print(f"Не найдено перемещение u{i}")
            return None
    res['displacements'] = u_values

    # 4. N1, N2 (опционально)
    n1_match = re.search(r'N1\s*=\s*([-\d.eE]+)', output)
    n2_match = re.search(r'N2\s*=\s*([-\d.eE]+)', output)
    res['N1'] = float(n1_match.group(1)) if n1_match else None
    res['N2'] = float(n2_match.group(1)) if n2_match else None

    return res

# --- СОХРАНЕНИЕ В БАЗУ ДАННЫХ ---
def init_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    # Таблица runs:
    # id, A12, A16, A22, A26, A66, N1, N2, u1x, u1y, u2x, u2y, ..., u16x, u16y
    col_defs = [
        "id INTEGER PRIMARY KEY AUTOINCREMENT",
        "A12 REAL", "A16 REAL", "A22 REAL", "A26 REAL", "A66 REAL",
        "N1 REAL", "N2 REAL"
    ]
    for i in range(1, NUM_POINTS+1):
        col_defs.append(f"P{i}x REAL")
        col_defs.append(f"P{i}y REAL")
        col_defs.append(f"u{i}x REAL")
        col_defs.append(f"u{i}y REAL")
    cursor.execute(f"CREATE TABLE IF NOT EXISTS runs ({', '.join(col_defs)})")
    conn.commit()
    return conn

def save_run(conn, a12, a16, a22, a26, a66, n1, n2, points, displacements):
    cursor = conn.cursor()
    values = [a12, a16, a22, a26, a66, n1, n2]
    for i in range(len(points)):
        x, y = points[i]
        ux, uy = displacements[i]
        values.append(x)
        values.append(y)
        values.append(ux)
        values.append(uy)
    placeholders = ','.join(['?'] * len(values))
    cursor.execute(f"INSERT INTO runs VALUES (NULL, {placeholders})", values)
    conn.commit()

# --- ОСНОВНОЙ ЦИКЛ ---
def main():
    if not os.path.exists(TEMPLATE_PDE):
        print(f"Ошибка: файл шаблона {TEMPLATE_PDE} не найден.")
        sys.exit(1)

    conn = init_database(DB_NAME)

    for run_idx in range(1, NUM_RUNS+1):
        print(f"Запуск {run_idx}/{NUM_RUNS}")
        # Генерируем Aij
        A12, A16, A22, A26, A66 = generate_random_Aij()
        # Запускаем FlexPDE
        output = run_flexpde(A12, A16, A22, A26, A66)
        # Парсим
        data = parse_flexpde_output(output, NUM_POINTS)
        if data is None:
            print(f"  Ошибка парсинга для A22={A22:.3f}")
            continue
        # Сохраняем в БД
        save_run(conn, A12, A16, A22, A26, A66, data['N1'], data['N2'], data['points'], data['displacements'])
        print(f"  Сохранено: N1={data['N1']:.2e}, N2={data['N2']:.2e}")

    conn.close()
    print(f"Готово. Результаты в {DB_NAME}")

main()