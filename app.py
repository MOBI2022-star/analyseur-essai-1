import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Dashboard Analyse & Suivi Interventions", layout="wide")

st.title("🚲 Application d'Analyse, de Suivi et de Contrôle des Interventions Vélos")
st.markdown("Analysez vos interventions par période, suivez la production de vos équipes, gérez les formulaires A/B/C, et comparez vos fichiers pour détecter les interventions perdues ou non soldées.")

# --- SECTION 1 : GESTION DES FICHIERS ET MEMOIRE (MULTI-FICHIERS) ---
st.sidebar.header("📁 Gestion des Fichiers & Mémoire")

uploaded_file = st.sidebar.file_uploader("Importer le fichier principal / actuel (.xls, .xlsx)", type=["xls", "xlsx"])
uploaded_file_compare = st.sidebar.file_uploader("Importer un ancien fichier (Optionnel - pour comparaison)", type=["xls", "xlsx"])

if uploaded_file is not None:
    @st.cache_data
    def load_data(file):
        return pd.read_excel(file)

    df = load_data(uploaded_file)
    
    # Normalisation des dates
    date_col_deb = "Date/heure de début de l'intervention"
    date_col_fin = "Date/heure de fin de l'intervention"
    
    if date_col_deb in df.columns:
        df[date_col_deb] = pd.to_datetime(df[date_col_deb], errors='coerce')
    if date_col_fin in df.columns:
        df[date_col_fin] = pd.to_datetime(df[date_col_fin], errors='coerce')
        
    # Filtre par période
    st.sidebar.header("🗓️ Filtrer par Période")
    min_date = df[date_col_deb].min().date() if date_col_deb in df.columns and not df[date_col_deb].isnull().all() else pd.to_datetime('2026-01-01').date()
    max_date = df[date_col_deb].max().date() if date_col_deb in df.columns and not df[date_col_deb].isnull().all() else pd.to_datetime('2026-12-31').date()
    
    start_date = st.sidebar.date_input("Date de début d'intervention", value=min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("Date de fin d'intervention", value=max_date, min_value=min_date, max_value=max_date)
    
    mask = (df[date_col_deb].dt.date >= start_date) & (df[date_col_deb].dt.date <= end_date)
    df_filtered = df.loc[mask].copy()
    
    st.sidebar.success(f"Données filtrées : {len(df_filtered)} / {len(df)} interventions.")
    
    if st.sidebar.button("🗑️ Vider la mémoire / cache"):
        st.cache_data.clear()
        st.rerun()

    if not df_filtered.empty:
        col_agent = "Assigné à l'acteur Libellé"
        col_form = "Identifiant du formulaire personnalisé"
        col_modele = "Modèle d'équipement"
        col_materiel = "Matériel"
        col_charge = "Charge prévue"
        col_code_int = "Code de l'intervention"
        col_etat = "Etat"
        
        # Conversion sécurisée de la charge en minutes
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
            
        df_filtered['Charge_Minutes'] = df_filtered[col_charge].apply(parse_charge) if col_charge in df_filtered.columns else 0.0

        # --- ONGLETS PRINCIPAUX ---
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📌 Tableaux Dynamiques", 
            "📈 Graphiques & KPI", 
            "🔍 Contrôle & Interventions Perdues", 
            "📝 Commentaires & Descriptions", 
            "📤 Fichiers à Partager"
        ])
        
        with tab1:
            st.subheader("1. Nombre de vélos / matériels sortis par agent")
            if col_agent in df_filtered.columns and col_materiel in df_filtered.columns:
                mat_agent = df_filtered.groupby(col_agent)[col_materiel].count().reset_index(name='Nombre de matériels sortis')
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
                    st.info(f"📌 **Total Général Formulaire C :** {total_c} (soit {pct_c_global:.2f}% du total général).")
                    
                if 'A' in form_pivot.columns and 'All' in form_pivot.index:
                    total_a = form_pivot.loc['All', 'A']
                    pct_a_global = (total_a / total_gen) * 100 if total_gen > 0 else 0
                    st.info(f"📌 **Total Général Formulaire A :** {total_a} (soit {pct_a_global:.2f}% du total général).")

            st.subheader("3. Total de charge prévue par agent")
            if col_agent in df_filtered.columns:
                charge_agent = df_filtered.groupby(col_agent)['Charge_Minutes'].sum().reset_index(name='Charge_Total_Minutes')
                charge_agent['Charge (heures)'] = (charge_agent['Charge_Total_Minutes'] / 60).round(2)
                st.dataframe(charge_agent[[col_agent, 'Charge (heures)']].rename(columns={col_agent: 'Agent'}), use_container_width=True)
                
            st.subheader("4. Nombre et pourcentages par Modèle d'Équipement (VAE & VLS)")
            if col_modele in df_filtered.columns:
                model_counts = df_filtered[col_modele].value_counts().reset_index()
                model_counts.columns = ['Modèle d’équipement', 'Nombre']
                model_counts['Pourcentage (%)'] = (model_counts['Nombre'] / model_counts['Nombre'].sum() * 100).round(2)
                st.dataframe(model_counts, use_container_width=True)

        with tab2:
            st.subheader("📈 Visualisations Graphiques Avancées")
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("**Matériels sortis par Agent (Barres)**")
                if col_agent in df_filtered.columns:
                    fig, ax = plt.subplots(figsize=(7, 4))
                    counts = df_filtered[col_agent].value_counts()
                    ax.bar(counts.index, counts.values, color='#2b5c8f')
                    plt.xticks(rotation=45, ha='right')
                    ax.set_ylabel("Nombre")
                    st.pyplot(fig)
                    
            with c2:
                st.markdown("**Répartition Modèles VAE / VLS (Camembert)**")
                if col_modele in df_filtered.columns:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    m_counts = df_filtered[col_modele].value_counts()
                    ax.pie(m_counts.values, labels=m_counts.index, autopct='%1.1f%%', startangle=90, colors=['#4CAF50', '#FF9800'])
                    st.pyplot(fig)
            
            # Option 5 : Courbe d'évolution du cumul des heures de travail par jour
            st.markdown("**Option 5 : Évolution du cumul des heures de travail par jour (Courbe)**")
            df_filtered['Date_Jour'] = df_filtered[date_col_deb].dt.date
            daily_charge = df_filtered.groupby('Date_Jour')['Charge_Minutes'].sum().reset_index()
            daily_charge['Cumul_Heures'] = (daily_charge['Charge_Minutes'].cumsum() / 60).round(2)
            
            fig_cumul, ax_cumul = plt.subplots(figsize=(10, 3.5))
            ax_cumul.plot(daily_charge['Date_Jour'], daily_charge['Cumul_Heures'], marker='s', color='#9b59b6', linewidth=2)
            ax_cumul.set_ylabel("Heures Cumulées")
            plt.xticks(rotation=45)
            ax_cumul.grid(True, linestyle='--', alpha=0.6)
            st.pyplot(fig_cumul)

            c3, c4 = st.columns(2)
            with c3:
                # Option 3 : Charge de travail totale par agent (Barres)
                st.markdown("**Option 3 : Charge de travail totale par Agent (Heures)**")
                if col_agent in df_filtered.columns:
                    fig_ch, ax_ch = plt.subplots(figsize=(7, 4))
                    ch_agent = df_filtered.groupby(col_agent)['Charge_Minutes'].sum() / 60
                    ax_ch.bar(ch_agent.index, ch_agent.values, color='#e67e22')
                    plt.xticks(rotation=45, ha='right')
                    ax_ch.set_ylabel("Heures")
                    st.pyplot(fig_ch)

            with c4:
                # Option 4 : Formulaires A, B, C par Agent (Barres groupées)
                st.markdown("**Option 4 : Répartition des Formulaires (A, B, C) par Agent**")
                if col_agent in df_filtered.columns and col_form in df_filtered.columns:
                    fig_form, ax_form = plt.subplots(figsize=(7, 4))
                    pivot_f = pd.crosstab(df_filtered[col_agent], df_filtered[col_form])
                    pivot_f.plot(kind='bar', ax=ax_form, colormap='Set2')
                    plt.xticks(rotation=45, ha='right')
                    ax_form.set_ylabel("Nombre")
                    st.pyplot(fig_form)

        with tab3:
            st.subheader("🔍 Module de Contrôle & Détection des Interventions Perdues")
            st.markdown("Ce module compare votre fichier historique/actuel avec un nouveau fichier pour détecter si des interventions ont disparues (non soldées ou supprimées par l'autre société).")
            
            if uploaded_file_compare is not None:
                df_old = pd.read_excel(uploaded_file_compare)
                
                if col_code_int in df_old.columns and col_code_int in df_filtered.columns:
                    # Recherche des interventions présentes dans l'ancien mais absentes dans le nouveau
                    missing_mask = ~df_old[col_code_int].isin(df_filtered[col_code_int])
                    df_lost = df_old.loc[missing_mask].copy()
                    
                    st.warning(f"⚠️ **{len(df_lost)} interventions perdues / supprimées** détectées par rapport au fichier de comparaison !")
                    if not df_lost.empty:
                        st.dataframe(df_lost[[col_code_int, col_agent, col_materiel, col_etat, 'Charge prévue']].dropna(how='all'), use_container_width=True)
                    else:
                        st.success("Aucune intervention perdue entre les deux fichiers.")
                else:
                    st.error(f"La colonne '{col_code_int}' est introuvable dans l'un des fichiers.")
            else:
                st.info("💡 Pour activer la comparaison, veuillez importer un ancien fichier dans la barre latérale gauche (sous l'import principal).")
            
            st.markdown("---")
            st.subheader("📋 Suivi des Statuts Actuels")
            if col_etat in df_filtered.columns:
                etat_counts = df_filtered[col_etat].value_counts().reset_index()
                etat_counts.columns = ['Statut / Etat', 'Nombre d’interventions']
                st.dataframe(etat_counts, use_container_width=True)
            
            # Barre de recherche rapide par numéro d'intervention ou de matériel
            search_query = st.text_input("🔍 Rechercher un Numéro d'intervention (ex: INT-...) ou un Vélo :")
            if search_query:
                mask_search = df_filtered.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                st.dataframe(df_filtered[mask_search], use_container_width=True)

        with tab4:
            st.subheader("📝 Commentaires et Descriptions Détaillées")
            cols_to_check = [col_agent, col_materiel, col_code_int, 'Contenu de la description détaillée', 'Texte libre 2', 'Texte libre 3', 'Texte libre 4', 'Texte libre 5']
            existing_cols = [c for c in cols_to_check if c in df_filtered.columns]
            
            if existing_cols:
                df_comments = df_filtered[existing_cols]
                st.write(f"Nombre total d'enregistrements : {len(df_comments)}")
                st.dataframe(df_comments, use_container_width=True)
            else:
                st.info("Aucune colonne de texte libre trouvée.")

        with tab5:
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
        st.warning("⚠️ Aucune donnée disponible pour la période sélectionnée.")
else:
    st.info("👋 Veuillez importer votre fichier Excel principal dans la barre latérale pour démarrer.")
