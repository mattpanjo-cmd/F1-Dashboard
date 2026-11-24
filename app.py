import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configurazione della pagina Streamlit
st.set_page_config(page_title="F1 Telemetry Dashboard", page_icon="🏎️", layout="wide")

# Palette colori ufficiale F1 per le mescole
COMPOUND_COLORS = {
    'SOFT': '#FF1801',          # Rosso
    'MEDIUM': '#FFD100',        # Giallo
    'HARD': '#FFFFFF',          # Bianco
    'INTERMEDIATE': '#39B54A',  # Verde
    'WET': '#00A2FF'            # Azzurro
}

st.title("🏎️ F1 Multi-Telemetry & Circuit Analyzer")
st.write("Dashboard professionale con mappa interattiva, numeri curve, start/finish line e comparazione multi-pilota.")

# --- SIDEBAR: CARICAMENTO DATI ---
st.sidebar.header("📁 Caricamento Dati")
laps_files = st.sidebar.file_uploader("Carica CSV dei Giri (uno o più file)", type=["csv"], accept_multiple_files=True, key="laps_multi")
telemetry_files = st.sidebar.file_uploader("Carica CSV della Telemetria (uno o più file)", type=["csv"], accept_multiple_files=True, key="tel_multi")
corners_file = st.sidebar.file_uploader("Carica CSV delle Curve (opzionale)", type=["csv"], key="corners_single")

# Mappa fissa del circuito nella Sidebar con Curve e Start/Finish Line
if telemetry_files:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🗺️ Mappa del Circuito")
    try:
        tf_map = telemetry_files[0]
        tf_map.seek(0)
        map_df = pd.read_csv(tf_map)
        if 'X' in map_df.columns and 'Y' in map_df.columns:
            if 'LapNumber' in map_df.columns:
                sample_lap = map_df['LapNumber'].dropna().iloc[0]
                track_map = map_df[map_df['LapNumber'] == sample_lap]
            else:
                track_map = map_df.head(1500)
                
            fig_map = go.Figure()
            # Tracciato del circuito
            fig_map.add_trace(go.Scatter(
                x=track_map['X'], y=track_map['Y'],
                mode='lines',
                line=dict(color='#00D2BE', width=2),
                name='Tracciato',
                hoverinfo='skip'
            ))
            
            # Se è caricato il file delle curve, aggiungiamo i numeri delle curve e la S/F line
            if corners_file is not None:
                corners_file.seek(0)
                df_corners = pd.read_csv(corners_file)
                if 'X' in df_corners.columns and 'Y' in df_corners.columns and 'Number' in df_corners.columns:
                    fig_map.add_trace(go.Scatter(
                        x=df_corners['X'], y=df_corners['Y'],
                        mode='text+markers',
                        text=df_corners['Number'].astype(str) + df_corners['Letter'].fillna(''),
                        textfont=dict(color='yellow', size=9),
                        marker=dict(size=5, color='yellow'),
                        name='Curve'
                    ))
            
            # Start / Finish line (primo punto del giro)
            if not track_map.empty:
                sf_x = track_map['X'].iloc[0]
                sf_y = track_map['Y'].iloc[0]
                fig_map.add_trace(go.Scatter(
                    x=[sf_x], y=[sf_y],
                    mode='markers+text',
                    marker=dict(size=10, color='red', symbol='square'),
                    text=['S/F'],
                    textfont=dict(color='red', size=10, weight='bold'),
                    name='Start/Finish'
                ))

            fig_map.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                paper_bgcolor='#0e1117',
                plot_bgcolor='#0e1117',
                showlegend=False,
                height=260
            )
            st.sidebar.plotly_chart(fig_map, use_container_width=True)
    except Exception as e:
        st.sidebar.info("Impossibile generare la mappa con i dati attuali.")

if laps_files:
    laps_dict = {}
    for f in laps_files:
        f.seek(0)
        df_temp = pd.read_csv(f)
        if 'LapTime' in df_temp.columns:
            df_temp['LapTime_sec'] = pd.to_timedelta(df_temp['LapTime']).dt.total_seconds()
            label = f.name.replace('.csv', '').replace('_', ' ').upper()
            laps_dict[label] = df_temp.dropna(subset=['LapTime_sec']).copy()

    if laps_dict:
        # --- METRICHE IN ALTO PER OGNI SET DI DATI CARICATO ---
        st.markdown("---")
        st.subheader("⚡ Riepilogo Giri Veloci per Set / Pilota")
        metric_cols = st.columns(len(laps_dict))
        
        for idx, (label, df_laps) in enumerate(laps_dict.items()):
            col = metric_cols[idx] if idx < len(metric_cols) else metric_cols[0]
            if not df_laps.empty:
                fastest_in_set = df_laps.loc[df_laps['LapTime_sec'].idxmin()]
                driver_code = str(fastest_in_set.get('Driver', label))
                lap_time_str = str(fastest_in_set['LapTime']).split()[-1]
                lap_num = int(fastest_in_set['LapNumber'])
                compound = str(fastest_in_set.get('Compound', 'N/A')).upper()
                
                col.metric(
                    label=f"🏁 {label}",
                    value=f"{lap_time_str} (Giro {lap_num})",
                    delta=f"Pilota: {driver_code} | Gomma: {compound}"
                )
        st.markdown("---")
        
        tab1, tab2 = st.tabs([
            "📊 Tempi sul Giro & Comparazione", 
            "🚀 Telemetria Velocità & Curve"
        ])
        
        def format_mmss(seconds):
            m = int(seconds // 60)
            s = seconds % 60
            return f"{m}:{s:06.3f}"

        # --- TAB 1: TEMPI SUL GIRO ---
        with tab1:
            st.subheader("📊 Evoluzione Tempi sul Giro (Comparazione Multi-Pilota)")
            
            fig1 = go.Figure()
            for label, df_laps in laps_dict.items():
                fig1.add_trace(go.Scatter(
                    x=df_laps['LapNumber'],
                    y=df_laps['LapTime_sec'],
                    mode='lines+markers',
                    name=label,
                    hovertemplate="<b>%{customdata[0]}</b><br>Giro: %{x}<br>Tempo: %{customdata[1]}<br>Gomma: %{customdata[2]}<extra></extra>",
                    customdata=list(zip(df_laps.get('Driver', label), df_laps['LapTime'], df_laps.get('Compound', 'N/A')))
                ))

            fig1.update_layout(
                template="plotly_dark",
                xaxis=dict(title="Numero Giro", gridcolor="rgba(128,128,128,0.2)"),
                yaxis=dict(title="Tempo sul Giro (Secondi)", gridcolor="rgba(128,128,128,0.2)"),
                paper_bgcolor='#0e1117', plot_bgcolor='#0e1117', font=dict(color='white'),
                height=500
            )
            st.plotly_chart(fig1, use_container_width=True)

            for label, df_laps in laps_dict.items():
                if 'Stint' in df_laps.columns:
                    st.markdown(f"### 🏎️ Medie Stint: {label}")
                    stint_summary = df_laps.groupby('Stint').agg(
                        avg_time=('LapTime_sec', 'mean'),
                        start_lap=('LapNumber', 'min'),
                        end_lap=('LapNumber', 'max'),
                        compound=('Compound', 'first')
                    ).reset_index()

                    stint_cols = st.columns(len(stint_summary) if len(stint_summary) > 0 else 1)
                    for idx, row in stint_summary.iterrows():
                        col = stint_cols[idx] if len(stint_cols) > idx else stint_cols[0]
                        col.metric(
                            label=f"Stint {int(row['Stint'])} ({str(row['compound']).upper()})",
                            value=format_mmss(row['avg_time']),
                            delta=f"Giri {int(row['start_lap'])}-{int(row['end_lap'])}",
                            delta_color="off"
                        )

        # --- TAB 2: TELEMETRIA VELOCITÀ COMPARATA CON SETTORI E CURVE ---
        with tab2:
            st.subheader("🚀 Comparazione Telemetria Velocità, Settori & Curve")
            
            if telemetry_files:
                tel_dict = {}
                for tf in telemetry_files:
                    tf.seek(0)
                    t_label = tf.name.replace('_telemetry.csv', '').replace('.csv', '').upper()
                    tel_dict[t_label] = pd.read_csv(tf)
                
                all_lap_options = []
                lap_mapping = {}
                
                for t_label, t_df in tel_dict.items():
                    if 'LapNumber' in t_df.columns:
                        laps_avail = sorted(t_df['LapNumber'].dropna().unique().astype(int))
                        for l in laps_avail:
                            option_text = f"{t_label} - Giro {l}"
                            all_lap_options.append(option_text)
                            lap_mapping[option_text] = (t_label, l)
                
                if all_lap_options:
                    selected_laps_to_compare = st.multiselect(
                        "Seleziona due o più giri da comparare in contemporanea:",
                        options=all_lap_options,
                        default=all_lap_options[:2] if len(all_lap_options) >= 2 else all_lap_options
                    )
                    
                    if selected_laps_to_compare:
                        fig3 = go.Figure()
                        compare_colors = ['#00D2BE', '#FF1801', '#FFD100', '#39B54A', '#00A2FF', '#9370DB', '#FF69B4']
                        
                        first_opt = selected_laps_to_compare[0]
                        f_label, f_lap = lap_mapping[first_opt]
                        matched_laps_df = None
                        for l_label, l_df in laps_dict.items():
                            if f_label.split()[0] in l_label:
                                matched_laps_df = l_df
                                break
                        if matched_laps_df is None and len(laps_dict) > 0:
                            matched_laps_df = list(laps_dict.values())[0]

                        if matched_laps_df is not None and 'Sector1Time' in matched_laps_df.columns:
                            lap_row = matched_laps_df[matched_laps_df['LapNumber'] == f_lap]
                            if not lap_row.empty:
                                s1_td = pd.to_timedelta(lap_row['Sector1Time'].values[0]).total_seconds()
                                s2_td = pd.to_timedelta(lap_row['Sector2Time'].values[0]).total_seconds()
                                sample_tel = tel_dict[f_label][tel_dict[f_label]['LapNumber'] == f_lap]
                                if not sample_tel.empty and 'Time' in sample_tel.columns:
                                    sample_tel = sample_tel.copy()
                                    sample_tel['Time_sec'] = pd.to_timedelta(sample_tel['Time']).dt.total_seconds()
                                    max_dist = sample_tel['Distance'].max()
                                    d_s1 = sample_tel[sample_tel['Time_sec'] <= s1_td]['Distance'].max()
                                    d_s2 = sample_tel[sample_tel['Time_sec'] <= (s1_td + s2_td)]['Distance'].max()
                                    
                                    if pd.isna(d_s1): d_s1 = max_dist * 0.33
                                    if pd.isna(d_s2): d_s2 = max_dist * 0.66

                                    fig3.add_vrect(x0=0, x1=d_s1, fillcolor="red", opacity=0.08, layer="below", line_width=0, annotation_text="Settore 1", annotation_position="top left")
                                    fig3.add_vrect(x0=d_s1, x1=d_s2, fillcolor="yellow", opacity=0.08, layer="below", line_width=0, annotation_text="Settore 2", annotation_position="top left")
                                    fig3.add_vrect(x0=d_s2, x1=max_dist, fillcolor="blue", opacity=0.08, layer="below", line_width=0, annotation_text="Settore 3", annotation_position="top left")

                        for idx, opt in enumerate(selected_laps_to_compare):
                            t_label, lap_num = lap_mapping[opt]
                            df_tel = tel_dict[t_label]
                            lap_tel = df_tel[df_tel['LapNumber'] == lap_num].copy()
                            
                            if not lap_tel.empty:
                                trace_color = compare_colors[idx % len(compare_colors)]
                                fig3.add_trace(go.Scatter(
                                    x=lap_tel['Distance'],
                                    y=lap_tel['Speed'],
                                    mode='lines',
                                    name=opt,
                                    line=dict(color=trace_color, width=2)
                                ))
                        
                        if corners_file is not None:
                            corners_file.seek(0)
                            df_corners = pd.read_csv(corners_file)
                            if 'Distance' in df_corners.columns and 'Number' in df_corners.columns:
                                for _, corner in df_corners.iterrows():
                                    d_val = corner['Distance']
                                    c_num = corner['Number']
                                    c_let = corner.get('Letter', '')
                                    if pd.isna(c_let): c_let = ''
                                    label_c = f"T{int(c_num)}{c_let}"
                                    
                                    fig3.add_vline(x=d_val, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)")
                                    fig3.add_annotation(
                                        x=d_val, y=1.02, yref="paper",
                                        text=label_c, showarrow=False,
                                        font=dict(color="yellow", size=9),
                                        textangle=-90
                                    )

                        fig3.update_layout(
                            template="plotly_dark",
                            xaxis=dict(title="Distanza Percorsa (metri)", gridcolor="rgba(128,128,128,0.2)"),
                            yaxis=dict(title="Velocità (km/h)", gridcolor="rgba(128,128,128,0.2)"),
                            paper_bgcolor='#0e1117', plot_bgcolor='#0e1117', font=dict(color='white'),
                            height=550,
                            legend_title="Giri a Confronto"
                        )
                        st.plotly_chart(fig3, use_container_width=True)
                    else:
                        st.info("Seleziona almeno un giro dal menu sopra per visualizzare il grafico della telemetria.")
                else:
                    st.warning("Nessun numero di giro trovato nei file di telemetria caricati.")
            else:
                st.info("👈 Carica i file CSV di telemetria dal menu laterale per sbloccare questa scheda.")
else:
    st.info("👈 Carica uno o più file CSV dei giri dalla barra laterale per avviare la dashboard.")
