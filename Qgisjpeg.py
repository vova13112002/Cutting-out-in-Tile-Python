import sqlite3
from io import BytesIO
from PIL import Image
from tkinter import filedialog, Tk

def remove_white_background(image):
    # Видаляємо білий фон (замінюємо білі пікселі на прозорі)
    image = image.convert("RGBA")
    data = image.getdata()
    new_data = []
    for item in data:
        # Якщо піксель не є білим, додаємо його до нового списку даних
        if item[:3] != (255, 255, 255):
            new_data.append(item)
        else:
            # Якщо піксель білий, замінюємо його на прозорий
            new_data.append((255, 255, 255, 0))

    # Створюємо нове зображення зі зміненими даними
    image.putdata(new_data)
    return image

def resize_and_crop_transparent_background(mbtiles_file, output_mbtiles_file):
    # Відкриємо з'єднання з MBTiles файлом
    conn = sqlite3.connect(mbtiles_file)
    cursor = conn.cursor()

    # Отримаємо список таблиць в базі даних (зазвичай є одна таблиця tiles)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Проходимося по кожному тайлу та змінюємо розмір зображення та вирізаємо прозорий фон
    for table in tables:
        if table[0] == 'tiles':  # Перевіряємо, чи таблиця називається 'tiles'
            cursor.execute(f"SELECT zoom_level, tile_column, tile_row, tile_data FROM {table[0]};")
            tiles = cursor.fetchall()

            for zoom_level, tile_column, tile_row, tile_data in tiles:
                # Зчитуємо тайл з даних MBTiles
                image = Image.open(BytesIO(tile_data))

                # Видаляємо білий фон
                image = remove_white_background(image)

                # Змінюємо розмір зображення та вирізаємо прозорий фон
                image = image.convert("RGBA")
                bbox = image.getbbox()
                cropped_image = image.crop(bbox)

                # Змінюємо розмір зображення до його власного розміру
                target_size = cropped_image.size
                resized_image = cropped_image.resize(target_size, Image.LANCZOS)

                # Визначаємо умову для видалення зображень (розмір менше 256x256)
                if resized_image.width >= 256 and resized_image.height >= 256:
                    # Конвертуємо зображення в режим "RGB" перед збереженням у JPEG
                    resized_image = resized_image.convert("RGB")
                    
                    # Зберігаємо змінений тайл назад у базу даних MBTiles
                    buffered = BytesIO()
                    resized_image.save(buffered, format="JPEG", quality=95)  # Зміни формату на JPEG та якість
                    tile_data = buffered.getvalue()

                    cursor.execute(f"UPDATE {table[0]} SET tile_data=? WHERE zoom_level=? AND tile_column=? AND tile_row=?;",
                                   (tile_data, zoom_level, tile_column, tile_row))
                else:
                    # Видаляємо зображення, якщо воно менше за 256x256
                    cursor.execute(f"DELETE FROM {table[0]} WHERE zoom_level=? AND tile_column=? AND tile_row=?;",
                                   (zoom_level, tile_column, tile_row))

    # Збережемо зміни та закриємо з'єднання
    conn.commit()
    conn.close()

    print("Зображення у MBTiles успішно змінено та вирізано!")

if __name__ == "__main__":
    root = Tk()
    root.withdraw()

    # Ask the user to choose the input MBTiles file using a file dialog
    input_mbtiles_file = filedialog.askopenfilename(title="Select Input MBTiles File", filetypes=[("MBTiles files", "*.mbtiles")])

    # Ask the user to choose the output MBTiles file using a file dialog
    output_mbtiles_file = filedialog.asksaveasfilename(title="Select Output MBTiles File", defaultextension=".mbtiles", filetypes=[("MBTiles files", "*.mbtiles")])

    # Check if the user has provided valid input and output file paths
    if input_mbtiles_file and output_mbtiles_file:
        # Call the function to resize, crop, remove white backgrounds, and save as JPEG
        resize_and_crop_transparent_background(input_mbtiles_file, output_mbtiles_file)
    else:
        print("Input or output file not selected. The process was aborted.")
