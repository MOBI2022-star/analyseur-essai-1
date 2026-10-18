import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io

st.set_page_config(page_title="Dashboard Analyse Interventions", layout="wide")

st.title("🚲 Application d'Analyse et de Suivi des Interventions Vélos")
st.markdown("Importez votre fichier Excel, sélectionnez une période d'intervention et analysez les performances de vos équipes (VAE, VLS, formulaires A/B/C, charges prévues et commentaires).")

# 1. Upload du fichier Excel
uploaded_file = st.file_uploader("📁 Importer votre fichier Excel (.xls, .xlsx)", type=["xls", "xlsx"])

if uploaded_file is not None:
    @st.cache_data
    def load_data(file):
        return pd.read_excel(file)

    df = load_data(uploaded_file)
    
    # Normalisation des noms de colonnes et des dates
    date_col_deb = "Date/heure de début de l'intervention"
    date_col_fin = "Date/heure de fin de l'intervention"
    
    if date_col_deb in df.columns:
        df[date_col_deb] = pd.to_datetime(df[date_col_deb], errors='coerce')
    if date_col_fin in df.columns:
        df[date_col_fin] = pd.to_datetime(df[date_col_fin], errors='coerce')
        
    st.sidebar.header("🗓️ Filtrer par Période")
    min_date = df[date_col_deb].min().date() if date_col_deb in df.columns and not df[date_col_deb].isnull().all() else pd.to_datetime('2026-01-01').date()
    max_date = df[date_col_deb].max().date() if date_col_deb in df.columns and not df[date_col_deb].isnull().all() else pd.to_datetime('2026-12-31').date()
    
    start_date = st.sidebar.date_input("Date de début d'intervention", value=min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("Date de fin d'intervention", value=max_date, min_value=min_date, max_value=max_date)
    
    # Filtrage des données
    mask = (df[date_col_deb].dt.date >= start_date) & (df[date_col_deb].dt.date <= end_date)
    df_filtered = df.loc[mask].copy()
    
    st.success(f"Données filtrées : {len(df_filtered)} interventions trouvées entre le {start_date} et le {end_date}.")
    
    # Bouton pour supprimer ou réinitialiser en mémoire si besoin
    if st.sidebar.button("🗑️ Vider le fichier de la mémoire"):
        st.cache_data.clear()
        st.rerun()

    if not df_filtered.empty:
        st.header("📊 Tableaux de Synthèse & Analyses de Production")
        
        col_agent = "Assigné à l'acteur Libellé"
        col_form = "Identifiant du formulaire personnalisé"
        col_modele = "Modèle d'équipement"
        col_materiel = "Matériel"
        col_charge = "Charge prévue"
        
        # Conversion de la charge en minutes ou heures si possible
        def parse_charge(val):
            if pd.isna(val):
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            try:
                parts = str(val).split(':')
                if len(parts) == 3:
                    return int(parts[0])*60 + int(parts[1]) + int(parts[2])/60
            except:
                pass
            return 0.0
            
        if col_charge in df_filtered.columns:
            df_filtered['Charge_Minutes'] = df_filtered[col_charge].apply(parse_charge)
        else:
            df_filtered['Charge_Minutes'] = 0.0

        tab1, tab2, tab3, tab4 = st.tabs(["📌 Tableaux Dynamiques", "📈 Graphiques & KPI", "📝 Commentaires & Descriptions", "📤 Fichiers à Partager"])
        
        with tab1:
            st.subheader("1. Nombre de vélos / matériels sortis par agent")
            if col_agent in df_filtered.columns and col_materiel in df_filtered.columns:
                mat_agent = df_filtered.groupby(col_agent)[col_materiel].count().reset_index()
                mat_agent.columns = ['Agent', 'Nombre de matériels sortis']
                st.dataframe(mat_agent, use_container_width=True)
            
            st.subheader("2. Identifiants de formulaires personnalisés (A, B, C) par agent & pourcentages")
            if col_agent in df_filtered.columns and col_form in df_filtered.columns:
                form_pivot = pd.crosstab(df_filtered[col_agent], df_filtered[col_form], margins=True)
                st.dataframe(form_pivot, use_container_width=True)
                
                st.markdown("### 📊 Pourcentages par rapport au Total Général")
                form_pct = pd.crosstab(df_filtered[col_agent], df_filtered[col_form], normalize='all') * 100
                st.dataframe(form_pct.round(2).astype(str) + ' %', use_container_width=True)
                
                total_gen = form_pivot.loc['All', 'All'] if 'All' in form_pivot.columns and 'All' in form_pivot.index else len(df_filtered)

                if 'C' in form_pivot.columns and 'All' in form_pivot.index:
                    total_c = form_pivot.loc['All', 'C']
                    pct_c_global = (total_c / total_gen) * 100 if total_gen > 0 else 0
                    st.info(f"📌 **Total Général Formulaire C :** {total_c} (soit {pct_c_global:.2f}% du total général des formulaires).")
                    
                if 'A' in form_pivot.columns and 'All' in form_pivot.index:
                    total_a = form_pivot.loc['All', 'A']
                    pct_a_global = (total_a / total_gen) * 100 if total_gen > 0 else 0
                    st.info(f"📌 **Total Général Formulaire A :** {total_a} (soit {pct_a_global:.2f}% du total général des formulaires).")

            st.subheader("3. Total de charge prévue par agent")
            if col_agent in df_filtered.columns:
                charge_agent = df_filtered.groupby(col_agent)['Charge_Minutes'].sum().reset_index()
                charge_agent['Charge (heures)'] = (charge_agent['Charge_Minutes'] / 60).round(2)
                st.dataframe(charge_agent[['Agent', 'Charge (heures)']], use_container_width=True)
                
            st.subheader("4. Nombre et pourcentages par Modèle d'Équipement (VAE & VLS)")
            if col_modele in df_filtered.columns:
                model_counts = df_filtered[col_modele].value_counts().reset_index()
                model_counts.columns = ['Modèle d’équipement', 'Nombre']
                model_counts['Pourcentage (%)'] = (model_counts['Nombre'] / model_counts['Nombre'].sum() * 100).round(2)
                st.dataframe(model_counts, use_container_width=True)

        with tab2:
            st.subheader("📈 Visualisations Graphiques")
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("**Matériels sortis par Agent (Barres)**")
                if col_agent in df_filtered.columns:
                    fig, ax = plt.subplots(figsize=(8, 5))
                    counts = df_filtered[col_agent].value_counts()
                    ax.bar(counts.index, counts.values, color='skyblue')
                    plt.xticks(rotation=45, ha='right')
                    ax.set_ylabel("Nombre")
                    st.pyplot(fig)
                    
            with c2:
                st.markdown("**Répartition Modèles VAE / VLS**")
                if col_modele in df_filtered.columns:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    m_counts = df_filtered[col_modele].value_counts()
                    ax.pie(m_counts.values, labels=m_counts.index, autopct='%1.1f%%', startangle=90, colors=['#ff9999','#66b3ff'])
                    st.pyplot(fig)
            
            st.markdown("**Évolution des interventions par jour (Courbe)**")
            df_filtered['Date_Jour'] = df_filtered[date_col_deb].dt.date
            daily_trend = df_filtered.groupby('Date_Jour').size().reset_index(name='Nombre_interventions')
            fig_line, ax_line = plt.subplots(figsize=(10, 4))
            ax_line.plot(daily_trend['Date_Jour'], daily_trend['Nombre_interventions'], marker='o', color='green', linewidth=2)
            plt.xticks(rotation=45)
            ax_line.set_ylabel("Interventions")
            st.pyplot(fig_line)

        with tab3:
            st.subheader("📝 Commentaires et Descriptions Détaillées")
            cols_to_check = ['Texte libre 2', 'Texte libre 3', 'Texte libre 4', 'Texte libre 5', 'Contenu de la description détaillée', 'Matériel', col_agent]
            existing_cols = [c for c in cols_to_check if c in df_filtered.columns]
            
            if existing_cols:
                df_comments = df_filtered[existing_cols].dropna(subset=[c for c in ['Texte libre 2', 'Contenu de la description détaillée'] if c in df_filtered.columns], how='all')
                st.write(f"Nombre total de lignes avec commentaires/descriptions : {len(df_comments)}")
                st.dataframe(df_comments, use_container_width=True)
            else:
                st.info("Aucune colonne de texte libre trouvée.")

        with tab4:
            st.subheader("📤 Export et Fichiers à Partager")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Rapport_Interventions')
            processed_data = output.getvalue()
            
            st.download_button(
                label="📥 Télécharger le rapport filtré (Excel)",
                data=processed_data,
                file_name="rapport_analyse_interventions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("Aucune donnée disponible pour la période sélectionnée.")
else:
    st.info("Veuillez importer un fichier Excel pour commencer.")
