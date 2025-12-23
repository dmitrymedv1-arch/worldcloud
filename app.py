import streamlit as st
from wordcloud import WordCloud
import io
import re
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
from PIL import Image

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
    .tab-content {
        padding: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Функции для обработки данных
def parse_frequency_input(text: str) -> dict[str, float]:
    """Парсинг ввода с частотами"""
    frequencies = {}
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Улучшенный парсинг с помощью regex
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
            continue
    
    return frequencies

def process_raw_text(text: str, stop_words: set = None) -> dict[str, int]:
    """Обработка сплошного текста и подсчет частот слов"""
    if stop_words is None:
        stop_words = set()
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Удаляем специальные символы, оставляем только слова
    words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]{3,}\b', text)
    
    # Фильтруем стоп-слова
    words = [word for word in words if word not in stop_words]
    
    # Подсчитываем частоты
    word_counts = Counter(words)
    
    # Нормализуем частоты
    if word_counts:
        max_count = max(word_counts.values())
        frequencies = {word: count / max_count for word, count in word_counts.items()}
        return frequencies
    
    return {}

def normalize_frequencies(frequencies: dict[str, float]) -> dict[str, float]:
    """Нормализация частот к диапазону 0-1"""
    if not frequencies:
        return frequencies
    
    max_freq = max(frequencies.values())
    
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
                            settings: dict) -> io.BytesIO:
    """Генерация изображения облака слов с высоким качеством"""
    if not frequencies:
        return None
    
    # Создаем фигуру с высоким DPI
    dpi = settings['dpi']
    width_inches = settings['width'] / dpi
    height_inches = settings['height'] / dpi
    
    fig, ax = plt.subplots(figsize=(width_inches, height_inches), dpi=dpi)
    
    # Создаем облако слов
    wordcloud = WordCloud(
        width=settings['width'],
        height=settings['height'],
        background_color=settings['background_color'],
        colormap=settings['colormap'],
        max_words=settings['max_words'],
        min_font_size=settings['min_font_size'],
        max_font_size=settings['max_font_size'],
        random_state=42,
        collocations=False,
        prefer_horizontal=0.8,
        margin=2,
        scale=settings.get('scale_factor', 1.0)
    )
    
    # Генерируем облако
    wordcloud.generate_from_frequencies(frequencies)
    
    # Отображаем на фигуре
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    
    # Сохраняем в буфер с высоким качеством
    buf = io.BytesIO()
    plt.savefig(buf, format='PNG', 
                dpi=dpi, 
                bbox_inches='tight', 
                pad_inches=0,
                facecolor=settings['background_color'])
    plt.close(fig)
    
    buf.seek(0)
    return buf

def generate_high_quality_image(frequencies: dict[str, float], 
                               settings: dict, 
                               format: str = 'PNG') -> io.BytesIO:
    """Генерация изображения в сверхвысоком качестве"""
    if not frequencies:
        return None
    
    # Создаем фигуру с высоким DPI для лучшего качества
    dpi = settings['dpi']
    width_inches = settings['width'] / dpi
    height_inches = settings['height'] / dpi
    
    fig, ax = plt.subplots(figsize=(width_inches, height_inches), dpi=dpi)
    
    # Создаем облако слов с улучшенными настройками
    wordcloud = WordCloud(
        width=settings['width'] * 2,
        height=settings['height'] * 2,
        background_color=settings['background_color'],
        colormap=settings['colormap'],
        max_words=settings['max_words'],
        min_font_size=settings['min_font_size'],
        max_font_size=settings['max_font_size'],
        random_state=42,
        collocations=False,
        prefer_horizontal=0.8,
        margin=2,
        scale=2.0
    )
    
    # Генерируем облако
    wordcloud.generate_from_frequencies(frequencies)
    
    # Отображаем на фигуре
    ax.imshow(wordcloud, interpolation='bicubic')
    ax.axis('off')
    
    # Сохраняем в выбранном формате
    buf = io.BytesIO()
    
    if format.upper() == 'PNG':
        plt.savefig(buf, format='PNG', 
                    dpi=dpi, 
                    bbox_inches='tight', 
                    pad_inches=0,
                    facecolor=settings['background_color'])
    elif format.upper() == 'PDF':
        plt.savefig(buf, format='PDF', 
                    dpi=dpi, 
                    bbox_inches='tight', 
                    pad_inches=0,
                    facecolor=settings['background_color'])
    elif format.upper() == 'SVG':
        plt.savefig(buf, format='SVG', 
                    bbox_inches='tight', 
                    pad_inches=0,
                    facecolor=settings['background_color'])
    elif format.upper() == 'JPG' or format.upper() == 'JPEG':
        plt.savefig(buf, format='JPEG', 
                    dpi=dpi, 
                    bbox_inches='tight', 
                    pad_inches=0,
                    facecolor=settings['background_color'],
                    quality=95)  # quality только для JPEG
    
    plt.close(fig)
    buf.seek(0)
    
    # Оптимизируем PNG с помощью PIL если нужно
    if format.upper() == 'PNG':
        try:
            from PIL import Image
            img = Image.open(buf)
            optimized_buf = io.BytesIO()
            img.save(optimized_buf, format='PNG', optimize=True)
            optimized_buf.seek(0)
            return optimized_buf
        except ImportError:
            pass
    
    buf.seek(0)
    return buf

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
            st.write(f"Качество DPI: **{settings['dpi']}**")
    
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
    
    # Топ-20 слов
    st.markdown("**🏆 Топ-20 слов по частоте:**")
    sorted_words = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Создаем DataFrame для красивого отображения
    df = pd.DataFrame(sorted_words, columns=['Слово', 'Частота'])
    df.index = df.index + 1
    
    # Отображаем в 2 колонки
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

# Основной интерфейс
st.markdown('<h1 class="main-header">☁️ Генератор облака слов</h1>', unsafe_allow_html=True)

# Боковая панель с настройками
with st.sidebar:
    st.header("⚙️ Настройки")
    
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
    
    # Другие настройки
    max_words = st.slider("Макс. слов", 10, 200, 50, 5)
    scale = st.slider("Масштаб частот", 0.1, 10.0, 1.0, 0.1)
    min_frequency = st.number_input("Мин. частота", 0.0, 1000.0, 0.0, 0.1)
    
    # Размеры облака
    width = st.slider("Ширина (px)", 400, 2000, 1200, 50)
    height = st.slider("Высота (px)", 300, 1500, 800, 50)
    
    # Настройки качества
    dpi = st.slider("Качество (DPI)", 72, 600, 300, 50)
    
    # Цвет фона
    background_color = st.color_picker("Цвет фона", "#FFFFFF")
    
    # Стоп-слова для обработки текста
    with st.expander("📝 Стоп-слова (для обработки текста)"):
        default_stopwords = """the and of to in a for that with as on at by from
        is are was were be been have has had this that these those
        they their them it its or but not what which who whom
        will would can could shall should may might must"""
        
        stop_words_input = st.text_area(
            "Введите стоп-слова (через пробел):",
            value=default_stopwords,
            height=100,
            help="Эти слова будут исключены из анализа текста"
        )
        
        # Преобразуем в множество для быстрого поиска
        stop_words = set(stop_words_input.lower().split())

# Основная область - вкладки для разных типов ввода
tab1, tab2 = st.tabs(["📊 С частотами слов", "📝 Сплошной текст"])

with tab1:
    st.markdown("### 📊 Ввод данных с частотами")
    
    with st.expander("📋 Форматы ввода"):
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
    
    # Поле ввода с частотами
    default_freq_data = """Materials science\t801
Chemistry\t698
Engineering\t395
Composite material\t473
Physics\t504
Chemical engineering\t308
Metallurgy\t391
Nanotechnology\t285
Biomaterials\t267"""

    freq_input_data = st.text_area(
        "Введите слова и частоты (каждое слово с новой строки):",
        value=default_freq_data,
        height=200,
        key="freq_input",
        label_visibility="collapsed"
    )
    
    input_mode = "frequency"

with tab2:
    st.markdown("### 📝 Ввод сплошного текста")
    
    with st.expander("ℹ️ Как это работает"):
        st.markdown("""
        **Функция анализа текста:**
        1. Текст разбивается на отдельные слова
        2. Удаляются стоп-слова (указаны в настройках)
        3. Считается частота каждого слова
        4. На основе частот генерируется облако слов
        
        **Пример текста для анализа:**
        """)
        st.code("""Special service environments challenge the metallic interconnector 
(MIC) of solid oxide fuel cells with high‐temperature oxidation, 
corrosion, and mechanical stresses under extreme conditions.""")
    
    # Поле ввода сплошного текста
    default_text_data = """Special service environments challenge the metallic interconnector (MIC) of solid oxide fuel cells with high‐temperature oxidation, corrosion, and mechanical stresses under extreme conditions. The degradation mechanisms affect performance and durability, requiring advanced materials and protective coatings for long-term operation in harsh environments."""

    text_input_data = st.text_area(
        "Введите или вставьте текст для анализа:",
        value=default_text_data,
        height=250,
        key="text_input",
        label_visibility="collapsed"
    )
    
    input_mode = "text"

# Предпросмотр
if input_mode == "frequency":
    parsed_data = parse_frequency_input(freq_input_data)
    if parsed_data:
        st.caption(f"✅ Распознано слов с частотами: {len(parsed_data)}")
    else:
        st.caption("ℹ️ Введите данные в указанном формате")
else:
    if text_input_data.strip():
        # Показываем предварительную статистику
        word_count = len(re.findall(r'\b\w+\b', text_input_data))
        st.caption(f"📝 Введено слов: {word_count} (стоп-слова будут исключены)")

# Кнопки управления
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_btn = st.button("🎯 Создать облако слов", use_container_width=True)

# Обработка генерации
if generate_btn:
    frequencies = {}
    total_words = 0
    
    if input_mode == "frequency":
        if not freq_input_data.strip():
            st.error("❌ Введите данные для генерации облака слов!")
            st.stop()
        
        with st.spinner("🔄 Обработка данных с частотами..."):
            frequencies = parse_frequency_input(freq_input_data)
            total_words = len(frequencies)
    
    elif input_mode == "text":
        if not text_input_data.strip():
            st.error("❌ Введите текст для анализа!")
            st.stop()
        
        with st.spinner("🔄 Анализ текста и подсчет частот..."):
            frequencies = process_raw_text(text_input_data, stop_words)
            total_words = sum(Counter(re.findall(r'\b\w+\b', text_input_data.lower())).values())
    
    if not frequencies:
        error_msg = "Не удалось распознать данные." if input_mode == "frequency" else "Не найдено значимых слов после фильтрации стоп-слов."
        st.error(f"❌ {error_msg}")
        st.stop()
    
    # Применяем нормализацию и фильтры
    frequencies = normalize_frequencies(frequencies)
    frequencies = apply_filters(frequencies, min_frequency, scale, max_words)
    
    if not frequencies:
        st.error(f"❌ Нет слов с частотой выше {min_frequency}!")
        st.stop()
    
    # Настройки для генерации
    settings = {
        'width': width,
        'height': height,
        'background_color': background_color,
        'colormap': color_schemes[selected_color],
        'max_words': max_words,
        'min_font_size': min_font_size,
        'max_font_size': max_font_size,
        'scale': scale,
        'min_frequency': min_frequency,
        'dpi': dpi,
        'scale_factor': 1.5  # Коэффициент для улучшения качества
    }
    
    # Генерация изображения
    with st.spinner("🎨 Генерация облака слов в высоком качестве..."):
        img_buffer = generate_wordcloud_image(frequencies, settings)
        high_quality_buffer = generate_high_quality_image(frequencies, settings, 'PNG')
    
    # Отображаем результат
    st.markdown("---")
    st.markdown("### ☁️ Результат")
    
    if img_buffer:
        # Отображаем изображение
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(img_buffer, use_container_width=True, caption="Предпросмотр")
        
        # Кнопки скачивания в разных форматах и качестве
        st.markdown("### 💾 Скачать изображение")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.download_button(
                label="⬇️ PNG (высокое качество)",
                data=high_quality_buffer,
                file_name="wordcloud_high_quality.png",
                mime="image/png",
                use_container_width=True,
                help=f"Разрешение: {width}x{height}px, DPI: {dpi}"
            )
        
        with col2:
            # PDF вариант
            pdf_buffer = generate_high_quality_image(frequencies, settings, 'PDF')
            st.download_button(
                label="⬇️ PDF (векторное)",
                data=pdf_buffer,
                file_name="wordcloud.pdf",
                mime="application/pdf",
                use_container_width=True,
                help="Векторный формат для печати"
            )
        
        with col3:
            # SVG вариант
            svg_buffer = generate_high_quality_image(frequencies, settings, 'SVG')
            st.download_button(
                label="⬇️ SVG (векторное)",
                data=svg_buffer,
                file_name="wordcloud.svg",
                mime="image/svg+xml",
                use_container_width=True,
                help="Масштабируемый векторный формат"
            )
        
        with col4:
            # Настройка DPI
            with st.popover("⚙️ Настроить качество"):
                custom_dpi = st.slider("DPI для сохранения", 72, 1200, 600, 50)
                custom_width = st.slider("Ширина (px)", 400, 4000, 2000, 100)
                custom_height = st.slider("Высота (px)", 300, 3000, 1500, 100)
                
                if st.button("🎨 Создать кастомное изображение"):
                    custom_settings = settings.copy()
                    custom_settings['dpi'] = custom_dpi
                    custom_settings['width'] = custom_width
                    custom_settings['height'] = custom_height
                    
                    with st.spinner(f"Создание изображения {custom_width}x{custom_height}px @ {custom_dpi}DPI..."):
                        custom_buffer = generate_high_quality_image(frequencies, custom_settings, 'PNG')
                        
                    st.download_button(
                        label=f"⬇️ Скачать ({custom_width}x{custom_height}px, {custom_dpi}DPI)",
                        data=custom_buffer,
                        file_name=f"wordcloud_{custom_width}x{custom_height}_{custom_dpi}dpi.png",
                        mime="image/png",
                        use_container_width=True
                    )
        
        # Статистика
        st.markdown("---")
        st.markdown("### 📊 Статистика")
        display_statistics(frequencies, total_words, settings)
        
        # Сохраняем в сессию для возможного повторного использования
        st.session_state['last_image'] = img_buffer.getvalue()
        st.session_state['last_frequencies'] = frequencies
        st.session_state['last_settings'] = settings
        st.session_state['total_words'] = total_words
        st.session_state['input_mode'] = input_mode

# Показываем последний результат если есть
elif 'last_image' in st.session_state:
    st.markdown("### ☁️ Последнее сгенерированное облако")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(st.session_state['last_image'], use_container_width=True)
    
    # Кнопки скачивания
    st.markdown("### 💾 Скачать изображение")
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="⬇️ PNG (высокое качество)",
            data=st.session_state['last_image'],
            file_name="wordcloud.png",
            mime="image/png",
            use_container_width=True
        )
    
    with col2:
        # Регенерация высококачественного изображения
        high_quality_buffer = generate_high_quality_image(
            st.session_state['last_frequencies'],
            st.session_state['last_settings'],
            'PNG'
        )
        st.download_button(
            label="⬇️ PNG (ультра качество)",
            data=high_quality_buffer,
            file_name="wordcloud_ultra_hq.png",
            mime="image/png",
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
        Поддерживает DPI до 600+ и анализ текста
    </div>
    """,
    unsafe_allow_html=True
)

