import streamlit as st
from wordcloud import WordCloud
import io
import re
import pandas as pd
from collections import Counter
import os
import tempfile
import base64
from PIL import ImageFont
import matplotlib.pyplot as plt
import numpy as np

# Настройка страницы
st.set_page_config(
    page_title="Генератор облака слов",
    page_icon="☁️",
    layout="wide"
)

# CSS стили
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .stButton>button {
        background-color: #3B82F6;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #2563EB;
    }
    .info-box {
        background-color: #F0F9FF;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #3B82F6;
        margin-bottom: 1rem;
    }
    .stat-box {
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
    }
    .word-count {
        font-size: 0.9rem;
        color: #6B7280;
        margin-top: 0.5rem;
    }
    .font-preview {
        font-size: 1.2rem;
        padding: 0.5rem;
        border-radius: 5px;
        background-color: #F8FAFC;
        margin: 0.5rem 0;
        border: 1px solid #E2E8F0;
    }
    .setting-group {
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Функции для обработки данных
def parse_input(text: str) -> dict[str, float]:
    """Парсинг ввода с улучшенной обработкой многословных терминов"""
    frequencies = {}
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Улучшенный парсинг с помощью regex
        # Ищем последнее число (возможно с % или /) в строке
        match = re.search(r'(.+?)\s+([-+]?\d*\.?\d+\s*%?)$', line.strip())
        
        if not match:
            # Пробуем старые форматы для совместимости
            if '\t' in line:
                parts = line.split('\t', 1)
            elif ':' in line:
                parts = line.split(':', 1)
            else:
                parts = re.split(r'\s+', line, 1)
            
            if len(parts) == 2:
                word = parts[0].strip()
                freq_str = parts[1].strip()
            else:
                continue
        else:
            word = match.group(1).strip()
            freq_str = match.group(2).strip()
        
        try:
            # Обработка процентов
            if '%' in freq_str:
                freq_str = freq_str.replace('%', '').strip()
                freq = float(freq_str)
                # Если процент > 1 (например 50%), делим на 100
                if freq > 1:
                    freq = freq / 100.0
            # Обработка дробей
            elif '/' in freq_str:
                num, denom = map(float, freq_str.split('/'))
                freq = num / denom
            else:
                freq = float(freq_str)
            
            if freq > 0:
                frequencies[word] = freq
                
        except ValueError:
            # Пропускаем строки с ошибками
            continue
    
    return frequencies

def normalize_frequencies(frequencies: dict[str, float]) -> dict[str, float]:
    """Нормализация частот к диапазону 0-1"""
    if not frequencies:
        return frequencies
    
    max_freq = max(frequencies.values())
    
    # Нормализуем только если есть большие числа
    if max_freq > 1.0:
        return {word: freq / max_freq for word, freq in frequencies.items()}
    
    return frequencies

def apply_filters(frequencies: dict[str, float], 
                  min_freq: float, 
                  scale: float, 
                  max_words: int) -> dict[str, float]:
    """Применение фильтров и масштабирования"""
    # Применяем минимальную частоту
    filtered = {k: v for k, v in frequencies.items() if v >= min_freq}
    
    if not filtered:
        return {}
    
    # Масштабируем
    scaled = {k: v * scale for k, v in filtered.items()}
    
    # Ограничиваем количество слов
    if len(scaled) > max_words:
        sorted_items = sorted(scaled.items(), key=lambda x: x[1], reverse=True)
        scaled = dict(sorted_items[:max_words])
    
    return scaled

@st.cache_data(show_spinner=False)
def generate_wordcloud_image(frequencies: dict[str, float], 
                            settings: dict,
                            font_path: str = None) -> tuple[io.BytesIO, io.BytesIO]:
    """Генерация изображения облака слов в PNG и JPEG форматах с кэшированием"""
    if not frequencies:
        return None, None
    
    # Создаем облако слов с учетом настроек ориентации
    wordcloud = WordCloud(
        width=settings['width'],
        height=settings['height'],
        background_color=settings['background_color'],
        colormap=settings['colormap'],
        max_words=settings['max_words'],
        min_font_size=settings['min_font_size'],
        max_font_size=settings['max_font_size'],
        prefer_horizontal=settings['prefer_horizontal'],
        margin=settings['margin'],
        random_state=42,
        collocations=False,
        font_path=font_path if font_path else None
    )
    
    # Генерируем облако
    wordcloud.generate_from_frequencies(frequencies)
    
    # Генерируем изображение с заданным DPI
    dpi = settings.get('dpi', 96)
    
    # Создаем фигуру matplotlib с нужным DPI
    fig = plt.figure(figsize=(settings['width']/dpi, settings['height']/dpi), dpi=dpi)
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    # PNG формат
    png_buf = io.BytesIO()
    fig.savefig(png_buf, format='PNG', dpi=dpi, bbox_inches='tight', pad_inches=0)
    png_buf.seek(0)
    
    # JPEG формат
    # Для JPEG меняем прозрачный фон на белый или выбранный цвет
    if settings['background_color'] == 'transparent':
        jpeg_background = '#FFFFFF'
    else:
        jpeg_background = settings['background_color']
    
    jpeg_buf = io.BytesIO()
    fig.savefig(jpeg_buf, format='JPEG', dpi=dpi, 
                bbox_inches='tight', pad_inches=0,
                facecolor=jpeg_background,
                quality=settings['jpeg_quality'])
    jpeg_buf.seek(0)
    
    plt.close(fig)
    
    return png_buf, jpeg_buf

def display_statistics(frequencies: dict[str, float], 
                      total_words: int,
                      settings: dict):
    """Отображение статистики"""
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("**📈 Основная статистика**")
            st.write(f"Всего слов: **{total_words}**")
            st.write(f"После фильтров: **{len(frequencies)}**")
            st.write(f"Мин. частота: **{settings['min_frequency']}**")
            st.write(f"Масштаб: **×{settings['scale']}**")
            st.write(f"DPI: **{settings['dpi']}**")
            st.write(f"Ориентация: **{settings['prefer_horizontal']*100:.0f}% гор.**")
    
    with col2:
        with st.container(border=True):
            st.markdown("**🎯 Диапазон частот**")
            if frequencies:
                min_val = min(frequencies.values())
                max_val = max(frequencies.values())
                avg_val = sum(frequencies.values()) / len(frequencies)
                st.write(f"Минимальная: **{min_val:.4f}**")
                st.write(f"Максимальная: **{max_val:.4f}**")
                st.write(f"Средняя: **{avg_val:.4f}**")
                st.write(f"Плотность (margin): **{settings['margin']}**")
                st.write(f"JPEG качество: **{settings['jpeg_quality']}%**")
    
    # Топ-20 слов
    st.markdown("**🏆 Топ-20 слов по частоте:**")
    sorted_words = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Создаем DataFrame для красивого отображения
    df = pd.DataFrame(sorted_words, columns=['Слово', 'Частота'])
    df.index = df.index + 1  # Начинаем с 1 вместо 0
    
    # Отображаем в 2 колонках
    col1, col2 = st.columns(2)
    half = len(df) // 2 + len(df) % 2
    
    with col1:
        st.dataframe(df.iloc[:half][['Слово', 'Частота']], 
                    use_container_width=True,
                    hide_index=False)
    
    with col2:
        if len(df) > half:
            st.dataframe(df.iloc[half:][['Слово', 'Частота']], 
                        use_container_width=True,
                        hide_index=False)

# Функция для получения доступных шрифтов
def get_available_fonts():
    """Возвращает список доступных шрифтов"""
    fonts = {
        "Стандартный (Arial)": None,
        "Times New Roman": "times.ttf",
        "Helvetica": "helvetica.ttf",
        "Georgia": "georgia.ttf",
        "Courier New": "cour.ttf",
        "Verdana": "verdana.ttf",
        "Tahoma": "tahoma.ttf",
        "Trebuchet MS": "trebuc.ttf",
        "Impact": "impact.ttf",
        "Comic Sans MS": "comic.ttf"
    }
    
    # Проверяем, какие шрифты доступны в системе
    available_fonts = {"Стандартный (Arial)": None}
    
    # Попробуем найти шрифты в типичных местах
    font_paths = [
        "C:/Windows/Fonts/",
        "/usr/share/fonts/",
        "/Library/Fonts/",
        "/System/Library/Fonts/"
    ]
    
    for font_name, font_file in fonts.items():
        if font_file is None:
            continue
            
        for font_path in font_paths:
            full_path = os.path.join(font_path, font_file)
            if os.path.exists(full_path):
                available_fonts[font_name] = full_path
                break
    
    return available_fonts

# Основной интерфейс
st.markdown('<h1 class="main-header">☁️ Генератор облака слов</h1>', unsafe_allow_html=True)

# Боковая панель с настройками
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Секция формат экспорта
    with st.container(border=True):
        st.markdown("**📁 Формат экспорта**")
        
        # Настройка DPI
        dpi = st.slider("DPI (качество)", 72, 300, 150, 1,
                       help="Чем выше DPI, тем лучше качество печати")
        
        # Настройка качества JPEG
        jpeg_quality = st.slider("Качество JPEG (%)", 50, 100, 90, 5,
                                help="Качество сжатия JPEG. 100% - наилучшее качество")
        
        # Выбор фонового цвета для JPEG (если фон прозрачный)
        st.markdown("**Цвет фона для JPEG:**")
        jpeg_bg_color = st.color_picker("", "#FFFFFF", label_visibility="collapsed",
                                       help="Цвет фона для JPEG (PNG поддерживает прозрачность)")
    
    # Секция оформления текста
    with st.container(border=True):
        st.markdown("**🎨 Оформление текста**")
        
        # Цветовые схемы
        color_schemes = {
            'Стандартная': 'viridis',
            'Пастельная': 'Pastel1',
            'Темная': 'plasma',
            'Яркая': 'Set2',
            'Односторонняя': 'coolwarm',
            'Теплая': 'hot',
            'Осенняя': 'autumn',
            'Радуга': 'rainbow'
        }
        
        selected_color = st.selectbox(
            "Цветовая схема",
            list(color_schemes.keys()),
            index=2
        )
        
        # Настройки размеров шрифта
        col1, col2 = st.columns(2)
        with col1:
            min_font_size = st.slider("Мин. шрифт", 5, 50, 10)
        with col2:
            max_font_size = st.slider("Макс. шрифт", 50, 400, 200)
        
        # Ориентация слов
        prefer_horizontal = st.slider(
            "Ориентация слов (% горизонт.)",
            0.0, 1.0, 0.8, 0.05,
            help="0% - только вертикальные слова, 100% - только горизонтальные"
        )
    
    # Секция выбора шрифта
    with st.container(border=True):
        st.markdown("**🔤 Шрифт**")
        
        # Получаем доступные шрифты
        available_fonts = get_available_fonts()
        
        font_option = st.radio(
            "Выберите шрифт:",
            ["Встроенный шрифт", "Загрузить свой шрифт"],
            index=0
        )
        
        selected_font = None
        
        if font_option == "Встроенный шрифт":
            font_names = list(available_fonts.keys())
            selected_font_name = st.selectbox(
                "Доступные шрифты:",
                font_names,
                index=0
            )
            selected_font = available_fonts[selected_font_name]
            
            # Превью шрифта
            if selected_font_name:
                st.markdown(f'<div class="font-preview" style="font-family: {selected_font_name.split(" (")[0]}, sans-serif;">Пример текста: Materials science</div>', unsafe_allow_html=True)
        
        else:  # Загрузка своего шрифта
            uploaded_font = st.file_uploader(
                "Загрузите файл шрифта (.ttf)",
                type=['ttf', 'otf']
            )
            
            if uploaded_font is not None:
                # Сохраняем временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as tmp_file:
                    tmp_file.write(uploaded_font.getvalue())
                    selected_font = tmp_file.name
                    st.session_state['uploaded_font_path'] = tmp_file.name
                
                st.success("✅ Шрифт загружен!")
                
                # Превью загруженного шрифта
                try:
                    font = ImageFont.truetype(selected_font, 16)
                    st.markdown(f'<div class="font-preview">Пример текста: Materials science</div>', unsafe_allow_html=True)
                except:
                    st.warning("Не удалось загрузить шрифт для предпросмотра")
    
    # Секция плотности и размера
    with st.container(border=True):
        st.markdown("**📐 Плотность и размер**")
        
        # Плотность (margin)
        margin = st.slider(
            "Плотность (расстояние между словами)",
            1, 20, 2, 1,
            help="Чем меньше значение, тем плотнее слова"
        )
        
        # Размеры облака
        col1, col2 = st.columns(2)
        with col1:
            width = st.slider("Ширина", 400, 1600, 1000, 50)
        with col2:
            height = st.slider("Высота", 300, 1200, 600, 50)
        
        # Цвет фона
        background_color = st.color_picker("Цвет фона", "#FFFFFF")
        
        # Другие настройки
        max_words = st.slider("Макс. слов", 10, 200, 50, 5)
        scale = st.slider("Масштаб частот", 0.1, 10.0, 1.0, 0.1)
        min_frequency = st.number_input("Мин. частота", 0.0, 1000.0, 0.0, 0.1)

# Основная область
with st.container():
    st.markdown("### 📝 Ввод данных")
    
    # Информационное окно
    with st.expander("📋 Форматы ввода (нажмите для просмотра)"):
        st.markdown("""
        **Поддерживаемые форматы:**
        - `Materials science 801` (целые числа)
        - `Chemistry 0.698` (десятичные дроби)
        - `Physics 50.40%` (проценты)
        - `Engineering 395` (табуляция или пробел)
        - `Composite material:473` (через двоеточие)
        
        **Пример:**
        ```
        Materials science 801
        Chemistry 698
        Engineering 395
        Composite material 473
        Physics 504
        ```
        """)
    
    # Поле ввода с примером
    default_data = """Materials science\t801
Chemistry\t698
Engineering\t395
Composite material\t473
Physics\t504
Chemical engineering\t308
Metallurgy\t391
Nanotechnology\t285
Biomaterials\t267"""

    input_data = st.text_area(
        "Введите слова и частоты (каждое слово с новой строки):",
        value=default_data,
        height=200,
        label_visibility="collapsed"
    )
    
    # Предпросмотр количества слов в реальном времени
    parsed_data = parse_input(input_data)
    if parsed_data:
        st.caption(f"✅ Распознано слов: {len(parsed_data)}")
    else:
        st.caption("ℹ️ Введите данные в указанном формате")

# Кнопки управления
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_btn = st.button("🎯 Создать облако слов", use_container_width=True)

# Обработка генерации
if generate_btn:
    if not input_data.strip():
        st.error("❌ Введите данные для генерации облака слов!")
        st.stop()
    
    with st.spinner("🔄 Обработка данных..."):
        # Парсим и обрабатываем данные
        frequencies = parse_input(input_data)
        
        if not frequencies:
            st.error("❌ Не удалось распознать данные. Проверьте формат ввода.")
            st.stop()
        
        total_words = len(frequencies)
        frequencies = normalize_frequencies(frequencies)
        frequencies = apply_filters(frequencies, min_frequency, scale, max_words)
        
        if not frequencies:
            st.error(f"❌ Нет слов с частотой выше {min_frequency}!")
            st.stop()
        
        # Определяем путь к шрифту
        font_path = None
        if 'uploaded_font_path' in st.session_state and os.path.exists(st.session_state['uploaded_font_path']):
            font_path = st.session_state['uploaded_font_path']
        elif selected_font:
            font_path = selected_font
        
        # Настройки для генерации
        settings = {
            'width': width,
            'height': height,
            'background_color': background_color,
            'colormap': color_schemes[selected_color],
            'max_words': max_words,
            'min_font_size': min_font_size,
            'max_font_size': max_font_size,
            'prefer_horizontal': prefer_horizontal,
            'margin': margin,
            'scale': scale,
            'min_frequency': min_frequency,
            'dpi': dpi,
            'jpeg_quality': jpeg_quality,
            'jpeg_background': jpeg_bg_color
        }
        
        # Генерируем изображение
        with st.spinner("🎨 Генерация облака слов..."):
            png_buffer, jpeg_buffer = generate_wordcloud_image(frequencies, settings, font_path)
        
        # Отображаем результат
        st.markdown("---")
        st.markdown("### ☁️ Результат")
        
        if png_buffer and jpeg_buffer:
            # Отображаем изображение
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(png_buffer, use_container_width=True, caption="Предпросмотр (PNG)")
            
            # Кнопки скачивания в двух колонках
            st.markdown("### 💾 Скачать")
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="⬇️ PNG (с прозрачностью)",
                    data=png_buffer,
                    file_name="wordcloud.png",
                    mime="image/png",
                    use_container_width=True,
                    help="PNG формат поддерживает прозрачность"
                )
            
            with col2:
                st.download_button(
                    label="⬇️ JPEG (высокое качество)",
                    data=jpeg_buffer,
                    file_name="wordcloud.jpg",
                    mime="image/jpeg",
                    use_container_width=True,
                    help=f"JPEG качество: {jpeg_quality}%, DPI: {dpi}"
                )
            
            # Статистика
            st.markdown("---")
            st.markdown("### 📊 Статистика")
            display_statistics(frequencies, total_words, settings)
            
            # Сохраняем в сессию для возможного повторного использования
            st.session_state['last_png_image'] = png_buffer.getvalue()
            st.session_state['last_jpeg_image'] = jpeg_buffer.getvalue()
            st.session_state['last_frequencies'] = frequencies
            st.session_state['last_settings'] = settings
            st.session_state['total_words'] = total_words
            st.session_state['font_path'] = font_path

# Показываем последний результат если есть
elif 'last_png_image' in st.session_state:
    st.markdown("### ☁️ Последнее сгенерированное облако")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(st.session_state['last_png_image'], use_container_width=True)
    
    # Кнопки скачивания
    st.markdown("### 💾 Скачать")
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="⬇️ PNG (с прозрачностью)",
            data=st.session_state['last_png_image'],
            file_name="wordcloud.png",
            mime="image/png",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            label="⬇️ JPEG (высокое качество)",
            data=st.session_state['last_jpeg_image'],
            file_name="wordcloud.jpg",
            mime="image/jpeg",
            use_container_width=True
        )
    
    # Статистика
    st.markdown("---")
    st.markdown("### 📊 Статистика")
    display_statistics(
        st.session_state['last_frequencies'],
        st.session_state['total_words'],
        st.session_state['last_settings']
    )

# Футер
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        @devloped by daM • WordCloud Generator • 
    </div>
    """,
    unsafe_allow_html=True
)
