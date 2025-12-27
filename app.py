import streamlit as st
from wordcloud import WordCloud
import io
import re
import pandas as pd
from collections import Counter

# Page configuration
st.set_page_config(
    page_title="Word Cloud Generator",
    page_icon="☁️",
    layout="wide"
)

# CSS styles
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
    </style>
""", unsafe_allow_html=True)

# Data processing functions
def parse_input(text: str) -> dict[str, float]:
    """Parse input with improved multi-word term handling"""
    frequencies = {}
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Improved parsing using regex
        # Find the last number (possibly with % or /) in the string
        match = re.search(r'(.+?)\s+([-+]?\d*\.?\d+\s*%?)$', line.strip())
        
        if not match:
            # Try old formats for compatibility
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
            # Handle percentages
            if '%' in freq_str:
                freq_str = freq_str.replace('%', '').strip()
                freq = float(freq_str)
                # If percentage > 1 (e.g., 50%), divide by 100
                if freq > 1:
                    freq = freq / 100.0
            # Handle fractions
            elif '/' in freq_str:
                num, denom = map(float, freq_str.split('/'))
                freq = num / denom
            else:
                freq = float(freq_str)
            
            if freq > 0:
                frequencies[word] = freq
                
        except ValueError:
            # Skip lines with errors
            continue
    
    return frequencies

def normalize_frequencies(frequencies: dict[str, float]) -> dict[str, float]:
    """Normalize frequencies to 0-1 range"""
    if not frequencies:
        return frequencies
    
    max_freq = max(frequencies.values())
    
    # Normalize only if there are large numbers
    if max_freq > 1.0:
        return {word: freq / max_freq for word, freq in frequencies.items()}
    
    return frequencies

def apply_filters(frequencies: dict[str, float], 
                  min_freq: float, 
                  scale: float, 
                  max_words: int) -> dict[str, float]:
    """Apply filters and scaling"""
    # Apply minimum frequency
    filtered = {k: v for k, v in frequencies.items() if v >= min_freq}
    
    if not filtered:
        return {}
    
    # Scale frequencies
    scaled = {k: v * scale for k, v in filtered.items()}
    
    # Limit number of words
    if len(scaled) > max_words:
        sorted_items = sorted(scaled.items(), key=lambda x: x[1], reverse=True)
        scaled = dict(sorted_items[:max_words])
    
    return scaled

@st.cache_data(show_spinner=False)
def generate_wordcloud_image(frequencies: dict[str, float], 
                            settings: dict) -> io.BytesIO:
    """Generate word cloud image with caching"""
    if not frequencies:
        return None
    
    # Create word cloud
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
        margin=2
    )
    
    # Generate word cloud
    wordcloud.generate_from_frequencies(frequencies)
    
    # Convert to PIL Image and then to BytesIO
    img = wordcloud.to_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True, quality=95)
    buf.seek(0)
    
    return buf

def display_statistics(frequencies: dict[str, float], 
                      total_words: int,
                      settings: dict):
    """Display statistics"""
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("**📈 Basic Statistics**")
            st.write(f"Total words: **{total_words}**")
            st.write(f"After filters: **{len(frequencies)}**")
            st.write(f"Min. frequency: **{settings['min_frequency']}**")
            st.write(f"Scale: **×{settings['scale']}**")
    
    with col2:
        with st.container(border=True):
            st.markdown("**🎯 Frequency Range**")
            if frequencies:
                min_val = min(frequencies.values())
                max_val = max(frequencies.values())
                avg_val = sum(frequencies.values()) / len(frequencies)
                st.write(f"Minimum: **{min_val:.4f}**")
                st.write(f"Maximum: **{max_val:.4f}**")
                st.write(f"Average: **{avg_val:.4f}**")
    
    # Top 20 words
    st.markdown("**🏆 Top 20 Words by Frequency:**")
    sorted_words = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Create DataFrame for nice display
    df = pd.DataFrame(sorted_words, columns=['Word', 'Frequency'])
    df.index = df.index + 1  # Start from 1 instead of 0
    
    # Display in 2 columns
    col1, col2 = st.columns(2)
    half = len(df) // 2 + len(df) % 2
    
    with col1:
        st.dataframe(df.iloc[:half][['Word', 'Frequency']], 
                    use_container_width=True,
                    hide_index=False)
    
    with col2:
        if len(df) > half:
            st.dataframe(df.iloc[half:][['Word', 'Frequency']], 
                        use_container_width=True,
                        hide_index=False)

# Main interface
st.markdown('<h1 class="main-header">☁️ Word Cloud Generator</h1>', unsafe_allow_html=True)

# Sidebar with settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Color schemes
    color_schemes = {
        'Standard': 'viridis',
        'Pastel': 'Pastel1',
        'Dark': 'plasma',
        'Bright': 'Set2',
        'Single Hue': 'coolwarm',
        'Warm': 'hot',
        'Autumn': 'autumn',
        'Rainbow': 'rainbow'
    }
    
    selected_color = st.selectbox(
        "Color Scheme",
        list(color_schemes.keys()),
        index=2
    )
    
    # Size settings
    col1, col2 = st.columns(2)
    with col1:
        min_font_size = st.slider("Min. font size", 5, 50, 10)
    with col2:
        max_font_size = st.slider("Max. font size", 50, 400, 200)
    
    # Other settings
    max_words = st.slider("Max. words", 10, 200, 50, 5)
    scale = st.slider("Frequency scale", 0.1, 10.0, 1.0, 0.1)
    min_frequency = st.number_input("Min. frequency", 0.0, 1000.0, 0.0, 0.1)
    
    # Cloud dimensions
    width = st.slider("Width", 400, 1600, 1000, 50)
    height = st.slider("Height", 300, 1200, 600, 50)
    
    # Background color
    background_color = st.color_picker("Background color", "#FFFFFF")

# Main area
with st.container():
    st.markdown("### 📝 Data Input")
    
    # Information box
    with st.expander("📋 Input Formats (click to view)"):
        st.markdown("""
        **Supported formats:**
        - `Materials science 801` (whole numbers)
        - `Chemistry 0.698` (decimal numbers)
        - `Physics 50.40%` (percentages)
        - `Engineering 395` (tab or space separated)
        - `Composite material:473` (colon separated)
        
        **Example:**
        ```
        Materials science 801
        Chemistry 698
        Engineering 395
        Composite material 473
        Physics 504
        ```
        """)
    
    # Input field with example
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
        "Enter words and frequencies (one per line):",
        value=default_data,
        height=200,
        label_visibility="collapsed"
    )
    
    # Real-time word count preview
    parsed_data = parse_input(input_data)
    if parsed_data:
        st.caption(f"✅ Words recognized: {len(parsed_data)}")
    else:
        st.caption("ℹ️ Enter data in the specified format")

# Control buttons
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    generate_btn = st.button("🎯 Generate Word Cloud", use_container_width=True)

# Processing generation
if generate_btn:
    if not input_data.strip():
        st.error("❌ Please enter data to generate word cloud!")
        st.stop()
    
    with st.spinner("🔄 Processing data..."):
        # Parse and process data
        frequencies = parse_input(input_data)
        
        if not frequencies:
            st.error("❌ Could not recognize data. Please check input format.")
            st.stop()
        
        total_words = len(frequencies)
        frequencies = normalize_frequencies(frequencies)
        frequencies = apply_filters(frequencies, min_frequency, scale, max_words)
        
        if not frequencies:
            st.error(f"❌ No words with frequency above {min_frequency}!")
            st.stop()
        
        # Settings for generation
        settings = {
            'width': width,
            'height': height,
            'background_color': background_color,
            'colormap': color_schemes[selected_color],
            'max_words': max_words,
            'min_font_size': min_font_size,
            'max_font_size': max_font_size,
            'scale': scale,
            'min_frequency': min_frequency
        }
        
        # Generate image
        with st.spinner("🎨 Generating word cloud..."):
            img_buffer = generate_wordcloud_image(frequencies, settings)
        
        # Display result
        st.markdown("---")
        st.markdown("### ☁️ Result")
        
        if img_buffer:
            # Display image
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(img_buffer, use_container_width=True)
            
            # Download button
            st.download_button(
                label="⬇️ Download Image (PNG)",
                data=img_buffer,
                file_name="wordcloud.png",
                mime="image/png",
                use_container_width=True
            )
            
            # Statistics
            st.markdown("---")
            st.markdown("### 📊 Statistics")
            display_statistics(frequencies, total_words, settings)
            
            # Save to session state for potential reuse
            st.session_state['last_image'] = img_buffer.getvalue()
            st.session_state['last_frequencies'] = frequencies
            st.session_state['last_settings'] = settings
            st.session_state['total_words'] = total_words

# Show last result if exists
elif 'last_image' in st.session_state:
    st.markdown("### ☁️ Last Generated Word Cloud")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(st.session_state['last_image'], use_container_width=True)
    
    # Download button
    st.download_button(
        label="⬇️ Download Image (PNG)",
        data=st.session_state['last_image'],
        file_name="wordcloud.png",
        mime="image/png",
        use_container_width=True
    )
    
    # Statistics
    st.markdown("---")
    st.markdown("### 📊 Statistics")
    display_statistics(
        st.session_state['last_frequencies'],
        st.session_state['total_words'],
        st.session_state['last_settings']
    )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        **•developed by @daM, @CTA, https://chimicatechnoacta.ru** 
    </div>
    """,
    unsafe_allow_html=True
)

