"""
NODAL - BFS 2024:1 Compliance Checker
Professional Web Application
"""

import streamlit as st
import tempfile
import os
import json
from datetime import datetime
from parser import parse_ifc
from geometry import check_multiple_spaces
from rules import BFS2024ComplianceChecker, generate_compliance_report

# Page configuration
st.set_page_config(
    page_title="NODAL - BFS 2024:1",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'language' not in st.session_state:
    st.session_state.language = 'en'
if 'results' not in st.session_state:
    st.session_state.results = None
if 'processed_file' not in st.session_state:
    st.session_state.processed_file = None

# Translations
TRANSLATIONS = {
    "en": {
        "header_subtitle": "BFS 2024:1 Accessibility Compliance Checker.",
        "header_desc": "Automated compliance checking for Swedish construction standards.",
        "upload_title": "Upload IFC File",
        "upload_subtitle": "Select an IFC file to check compliance.",
        "file_uploaded": "File uploaded",
        "check_button": "CHECK COMPLIANCE",
        "processing": "Processing...",
        "parsing": "Parsing IFC file...",
        "geometry_check": "Running geometry checks on",
        "compliance_check": "Checking BFS 2024:1 compliance...",
        "complete": "Compliance check complete!",
        "error_no_spaces": "No spaces found in IFC file",
        "results_title": "Compliance Results",
        "total_spaces": "Total Spaces",
        "passed": "Passed",
        "failed": "Failed",
        "partial": "Partial",
        "detailed_results": "Detailed Results",
        "space_id": "Space ID",
        "type": "Type",
        "overall_status": "Overall Status",
        "checked": "Checked",
        "compliance_checks": "Compliance Checks",
        "severity": "Severity",
        "export_results": "Export Results",
        "download_json": "Download JSON Report",
        "download_text": "Download Text Report",
        "upload_prompt": "Upload an IFC file above to begin compliance checking",
        "spaces": "spaces",
        "footer_title": "BFS 2024:1 – Automated Compliance | Built for Swedish Construction Industry",
        "footer_tagline": "Ensure accessibility requirements are met through automated geometric analysis.",
        "footer_copyright": "© 2026 NODAL | Stockholm, Sweden"
    },
    "sv": {
        "header_subtitle": "BFS 2024:1 – Automatiserad regelefterlevnad",
        "header_desc": "Byggd för svensk byggindustri.",
        "upload_title": "Ladda upp IFC-fil",
        "upload_subtitle": "Välj en IFC-fil för att kontrollera regelefterlevnad",
        "file_uploaded": "Fil uppladdad",
        "check_button": "KONTROLLERA REGELEFTERLEVNAD",
        "processing": "Bearbetar...",
        "parsing": "Analyserar IFC-fil...",
        "geometry_check": "Kör geometrikontroller på",
        "compliance_check": "Kontrollerar BFS 2024:1-regelefterlevnad...",
        "complete": "Regelefterlevnadskontroll slutförd!",
        "error_no_spaces": "Inga utrymmen hittades i IFC-filen",
        "results_title": "Resultat för regelefterlevnad",
        "total_spaces": "Totalt antal utrymmen",
        "passed": "Godkänt",
        "failed": "Underkänt",
        "partial": "Delvis",
        "detailed_results": "Detaljerade resultat",
        "space_id": "Utrymmes-ID",
        "type": "Typ",
        "overall_status": "Övergripande status",
        "checked": "Kontrollerad",
        "compliance_checks": "Regelefterlevnadskontroller",
        "severity": "Allvarlighetsgrad",
        "export_results": "Exportera resultat",
        "download_json": "Ladda ner JSON-rapport",
        "download_text": "Ladda ner textrapport",
        "upload_prompt": "Ladda upp en IFC-fil ovan för att börja regelefterlevnadskontrollen",
        "spaces": "utrymmen",
        "footer_title": "BFS 2024:1 – Automatiserad regelefterlevnad | Byggd för svensk byggindustri",
        "footer_tagline": "Säkerställer att tillgänglighetskraven uppfylls genom automatiserad geometrianalys.",
        "footer_copyright": "© 2026 NODAL | Stockholm, Sverige"
    }
}

def t(key):
    """Get translation"""
    lang = st.session_state.language
    return TRANSLATIONS[lang].get(key, key)

# Professional CSS with RED theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide ALL Streamlit branding */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    
    /* Dark red background */
    .stApp {
        background: #1a0a0f;
    }
    
    /* RED gradient header */
    .main-header {
        background: linear-gradient(135deg, #8B0000 0%, #DC143C 40%, #FF6347 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        margin-bottom: 3rem;
        box-shadow: 0 10px 40px rgba(139,0,0,0.4);
    }
    
    .logo-container {
        display: flex;
        align-items: center;
        gap: 20px;
        margin-bottom: 1rem;
    }
    
    .logo-icon {
        font-size: 4rem;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
    }
    
    .logo-text {
        font-size: 4rem;
        font-weight: 900;
        letter-spacing: -3px;
        color: white;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.4);
    }
    
    .header-subtitle {
        font-size: 1.3rem;
        color: rgba(255,255,255,0.95);
        font-weight: 500;
        margin-top: 0.5rem;
    }
    
    .header-desc {
        font-size: 1rem;
        color: rgba(255,255,255,0.85);
        margin-top: 0.75rem;
    }
    
    /* Upload section */
    .upload-section {
        background: rgba(255,255,255,0.03);
        border: 2px dashed rgba(139,0,0,0.3);
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
    }
    
    /* Metric cards with red accents */
    .metric-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid rgba(255,255,255,0.1);
        border-left: 5px solid;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(220,20,60,0.2);
    }
    
    .metric-card.success { border-left-color: #28a745; }
    .metric-card.danger { border-left-color: #DC143C; }
    .metric-card.warning { border-left-color: #FF6347; }
    
    .metric-value {
        font-size: 3.5rem;
        font-weight: 900;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.6);
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
    }
    
    /* RED buttons */
    .stButton > button {
        background: linear-gradient(135deg, #8B0000 0%, #DC143C 100%) !important;
        color: white !important;
        border: none !important;
        padding: 1.2rem 3rem !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        box-shadow: 0 6px 20px rgba(220,20,60,0.4) !important;
        transition: all 0.3s ease !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 30px rgba(220,20,60,0.6) !important;
        background: linear-gradient(135deg, #DC143C 0%, #FF6347 100%) !important;
    }
    
    /* Download buttons */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%) !important;
        color: white !important;
        border: none !important;
        padding: 1rem 2rem !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
    }
    
    /* Language selector */
    .stSelectbox {
        margin-top: 1rem;
    }
    
    /* Text color */
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: rgba(255,255,255,0.95) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        font-weight: 600 !important;
    }
    
    /* Footer with red gradient */
    .footer {
        background: linear-gradient(135deg, rgba(139,0,0,0.15) 0%, rgba(220,20,60,0.1) 100%);
        border-radius: 15px;
        padding: 2rem;
        margin-top: 3rem;
        text-align: center;
        border: 1px solid rgba(139,0,0,0.2);
    }
    
    .footer-title {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #DC143C 0%, #FF6347 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .footer-text {
        color: rgba(255,255,255,0.6);
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Header with language toggle
col_header, col_lang = st.columns([5, 1])

with col_header:
    st.markdown(f"""
    <div class="main-header">
        <div class="logo-container">
            <div class="logo-icon">🏗️</div>
            <div class="logo-text">NODAL</div>
        </div>
        <div class="header-subtitle">{t('header_subtitle')}</div>
        <div class="header-desc">{t('header_desc')}</div>
    </div>
    """, unsafe_allow_html=True)

with col_lang:
    language = st.selectbox(
        "Language",
        ["🇬🇧 English", "🇸🇪 Svenska"],
        index=0 if st.session_state.language == 'en' else 1,
        label_visibility="collapsed"
    )
    st.session_state.language = "sv" if "Svenska" in language else "en"

# Upload section
st.markdown(f"## 📁 {t('upload_title')}")

uploaded_file = st.file_uploader(
    t('upload_subtitle'),
    type=['ifc'],
    label_visibility="collapsed"
)

if uploaded_file:
    st.success(f"✓ {t('file_uploaded')}: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(f"🔍 {t('check_button')}", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ifc') as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name
            
            try:
                with st.spinner(t('processing')):
                    status = st.empty()
                    
                    status.info(f"📖 {t('parsing')}")
                    parsed = parse_ifc(tmp_path)
                    spaces = parsed.get("spaces", [])
                    
                    if not spaces:
                        st.error(f"❌ {t('error_no_spaces')}")
                        st.stop()
                    
                    status.info(f"📐 {t('geometry_check')} {len(spaces)} {t('spaces')}...")
                    geometry_results = check_multiple_spaces(spaces)
                    
                    status.info(f"✓ {t('compliance_check')}")
                    checker = BFS2024ComplianceChecker()
                    compliance_results = []
                    
                    for i, space in enumerate(spaces):
                        result = checker.check_compliance(space, geometry_results[i])
                        compliance_results.append(result)
                    
                    status.success(f"✓ {t('complete')}")
                    
                    st.session_state.results = compliance_results
                    st.session_state.processed_file = uploaded_file.name
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            finally:
                os.unlink(tmp_path)

# Results
if st.session_state.results:
    st.markdown("---")
    st.markdown(f"## 📊 {t('results_title')}")
    
    results = st.session_state.results
    passed = sum(1 for r in results if r.overall_status.value == "PASS")
    failed = sum(1 for r in results if r.overall_status.value == "FAIL")
    partial = sum(1 for r in results if r.overall_status.value == "PARTIAL")
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(results)}</div>
            <div class="metric-label">{t('total_spaces')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        st.markdown(f"""
        <div class="metric-card success">
            <div class="metric-value" style="color: #28a745;">✓ {passed}</div>
            <div class="metric-label">{t('passed')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c3:
        st.markdown(f"""
        <div class="metric-card danger">
            <div class="metric-value" style="color: #DC143C;">✗ {failed}</div>
            <div class="metric-label">{t('failed')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with c4:
        st.markdown(f"""
        <div class="metric-card warning">
            <div class="metric-value" style="color: #FF6347;">⚠ {partial}</div>
            <div class="metric-label">{t('partial')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Detailed results
    st.markdown(f"### 📋 {t('detailed_results')}")
    
    for result in results:
        icon = "✓" if result.overall_status.value == "PASS" else "✗" if result.overall_status.value == "FAIL" else "⚠"
        
        with st.expander(f"{icon} **{result.space_name}** ({result.space_type}) - {result.overall_status.value}",
                        expanded=(result.overall_status.value == "FAIL")):
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**{t('space_id')}:** `{result.space_id}`")
                st.markdown(f"**{t('type')}:** {result.space_type}")
            with col2:
                st.markdown(f"**{t('overall_status')}:** {result.overall_status.value}")
                st.markdown(f"**{t('checked')}:** {result.timestamp.split('T')[1].split('.')[0]}")
            
            st.markdown("---")
            st.markdown(f"**{t('compliance_checks')}:**")
            
            for rule in result.rules_checked:
                colors = {"PASS": "#28a745", "FAIL": "#DC143C", "NOT_APPLICABLE": "#6c757d", 
                         "NOT_CHECKED": "#FF6347", "ERROR": "#DC143C"}
                icons = {"PASS": "✓", "FAIL": "✗", "NOT_APPLICABLE": "-", "NOT_CHECKED": "?", "ERROR": "!"}
                
                color = colors.get(rule.status.value, "#666")
                icon = icons.get(rule.status.value, "?")
                
                st.markdown(f"""
                <div style="padding: 1rem; margin: 0.5rem 0; background: rgba(255,255,255,0.05); 
                            border-radius: 10px; border-left: 4px solid {color};">
                    <div style="font-weight: 700; color: {color}; font-size: 1.05rem;">
                        {icon} {rule.rule_name}
                    </div>
                    <div style="font-size: 0.85rem; color: rgba(255,255,255,0.6); margin-top: 0.3rem;">
                        {rule.reference} | {t('severity')}: {rule.severity.value}
                    </div>
                    <div style="margin-top: 0.6rem; font-size: 0.95rem; color: rgba(255,255,255,0.8);">
                        {rule.details}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Export
    st.markdown("---")
    st.markdown(f"### 💾 {t('export_results')}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        json_data = {
            "file": st.session_state.processed_file,
            "timestamp": datetime.now().isoformat(),
            "language": st.session_state.language,
            "results": [r.to_dict() for r in results]
        }
        
        st.download_button(
            label=f"📄 {t('download_json')}",
            data=json.dumps(json_data, indent=2, ensure_ascii=False),
            file_name=f"nodal_compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        text_report = generate_compliance_report(results, include_passed=True)
        
        st.download_button(
            label=f"📋 {t('download_text')}",
            data=text_report,
            file_name=f"nodal_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    st.info(f"👆 {t('upload_prompt')}")

# Footer
st.markdown(f"""
<div class="footer">
    <div class="footer-title">NODAL</div>
    <div class="footer-text">{t('footer_title')}</div>
    <div class="footer-text" style="margin-top: 0.5rem; font-style: italic;">
        {t('footer_tagline')}
    </div>
    <div class="footer-text" style="margin-top: 1rem;">
        {t('footer_copyright')}
    </div>
</div>
""", unsafe_allow_html=True)