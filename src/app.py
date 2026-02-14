"""
NODAL - BFS 2024:1 Compliance Checker
Professional Streamlit Dashboard
"""

import streamlit as st
import tempfile
import os
import json
from datetime import datetime
from parser import parse_ifc
from geometry import check_multiple_spaces
from rules import BFS2024ComplianceChecker, generate_compliance_report, export_results_json

# Page configuration
st.set_page_config(
    page_title="NODAL - BFS 2024:1 Compliance",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional appearance
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-blue: #005293;
        --primary-yellow: #FECC00;
        --success-green: #28a745;
        --danger-red: #dc3545;
        --warning-yellow: #ffc107;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #005293 0%, #0066b3 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.2rem;
        opacity: 0.9;
    }
    
    /* Card styling */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid;
        margin-bottom: 1rem;
    }
    
    .metric-card.success {
        border-left-color: #28a745;
    }
    
    .metric-card.danger {
        border-left-color: #dc3545;
    }
    
    .metric-card.warning {
        border-left-color: #ffc107;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.25rem;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .status-pass {
        background-color: #d4edda;
        color: #155724;
    }
    
    .status-fail {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    .status-partial {
        background-color: #fff3cd;
        color: #856404;
    }
    
    /* Upload section */
    .upload-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border: 2px dashed #005293;
        text-align: center;
        margin: 2rem 0;
    }
    
    /* Results table */
    .results-table {
        width: 100%;
        margin-top: 2rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <div class="main-title">🏗️ NODAL</div>
    <div class="subtitle">BFS 2024:1 Accessibility Compliance Checker</div>
    <div style="margin-top: 1rem; font-size: 0.9rem;">
        Automated compliance checking for Swedish construction standards
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'processed_file' not in st.session_state:
    st.session_state.processed_file = None

# File upload section
st.markdown("### 📁 Upload IFC File")

uploaded_file = st.file_uploader(
    "Select an IFC file to check compliance",
    type=['ifc'],
    help="Upload your building model in IFC format (Industry Foundation Classes)"
)

if uploaded_file is not None:
    st.success(f"✓ File uploaded: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
    
    # Process button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Check Compliance", type="primary", use_container_width=True):
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ifc') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Processing with status updates
                with st.spinner("Processing..."):
                    # Step 1: Parse IFC
                    status_placeholder = st.empty()
                    status_placeholder.info("📖 Parsing IFC file...")
                    
                    parsed_data = parse_ifc(tmp_path)
                    spaces = parsed_data.get("spaces", [])
                    
                    if not spaces:
                        st.error("❌ No spaces found in IFC file. Please check your file format.")
                        st.stop()
                    
                    # Step 2: Geometry checks
                    status_placeholder.info(f"📐 Running geometry checks on {len(spaces)} spaces...")
                    geometry_results = check_multiple_spaces(spaces)
                    
                    # Step 3: Compliance checks
                    status_placeholder.info("✓ Checking BFS 2024:1 compliance...")
                    checker = BFS2024ComplianceChecker()
                    compliance_results = []
                    
                    for i, space in enumerate(spaces):
                        geometry_result = geometry_results[i]
                        compliance_result = checker.check_compliance(space, geometry_result)
                        compliance_results.append(compliance_result)
                    
                    status_placeholder.success("✓ Compliance check complete!")
                    
                    # Store results in session state
                    st.session_state.results = compliance_results
                    st.session_state.processed_file = uploaded_file.name
                    
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
                st.exception(e)
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

# Display results
if st.session_state.results:
    st.markdown("---")
    st.markdown("## 📊 Compliance Results")
    
    results = st.session_state.results
    
    # Summary metrics
    passed_count = sum(1 for r in results if r.overall_status.value == "PASS")
    failed_count = sum(1 for r in results if r.overall_status.value == "FAIL")
    partial_count = sum(1 for r in results if r.overall_status.value == "PARTIAL")
    
    # Metric cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(results)}</div>
            <div class="metric-label">Total Spaces</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card success">
            <div class="metric-value" style="color: #28a745;">✓ {passed_count}</div>
            <div class="metric-label">Passed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card danger">
            <div class="metric-value" style="color: #dc3545;">✗ {failed_count}</div>
            <div class="metric-label">Failed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card warning">
            <div class="metric-value" style="color: #ffc107;">⚠ {partial_count}</div>
            <div class="metric-label">Partial</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Detailed results
    st.markdown("### 📋 Detailed Results")
    
    for result in results:
        # Determine status color and icon
        if result.overall_status.value == "PASS":
            status_class = "status-pass"
            status_icon = "✓"
        elif result.overall_status.value == "FAIL":
            status_class = "status-fail"
            status_icon = "✗"
        else:
            status_class = "status-partial"
            status_icon = "⚠"
        
        # Create expander for each space
        with st.expander(
            f"{status_icon} **{result.space_name}** ({result.space_type}) - {result.overall_status.value}",
            expanded=(result.overall_status.value == "FAIL")
        ):
            # Space info
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Space ID:** `{result.space_id}`")
                st.markdown(f"**Type:** {result.space_type}")
            with col2:
                st.markdown(f"**Overall Status:** {result.overall_status.value}")
                st.markdown(f"**Checked:** {result.timestamp.split('T')[1].split('.')[0]}")
            
            st.markdown("---")
            
            # Rule checks
            st.markdown("**Compliance Checks:**")
            
            for rule in result.rules_checked:
                # Icon based on status
                if rule.status.value == "PASS":
                    icon = "✓"
                    color = "#28a745"
                elif rule.status.value == "FAIL":
                    icon = "✗"
                    color = "#dc3545"
                elif rule.status.value == "NOT_APPLICABLE":
                    icon = "-"
                    color = "#6c757d"
                elif rule.status.value == "NOT_CHECKED":
                    icon = "?"
                    color = "#ffc107"
                else:
                    icon = "!"
                    color = "#dc3545"
                
                # Display rule result
                st.markdown(f"""
                <div style="padding: 0.75rem; margin: 0.5rem 0; background: #f8f9fa; border-radius: 5px; border-left: 3px solid {color};">
                    <div style="font-weight: 600; color: {color};">
                        {icon} {rule.rule_name}
                    </div>
                    <div style="font-size: 0.85rem; color: #666; margin-top: 0.25rem;">
                        {rule.reference} | Severity: {rule.severity.value}
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 0.9rem;">
                        {rule.details}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Export options
    st.markdown("---")
    st.markdown("### 💾 Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON export
        json_data = {
            "file": st.session_state.processed_file,
            "timestamp": datetime.now().isoformat(),
            "results": [r.to_dict() for r in results]
        }
        
        json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        
        st.download_button(
            label="📄 Download JSON Report",
            data=json_str,
            file_name=f"nodal_compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        # Text report
        text_report = generate_compliance_report(results, include_passed=True)
        
        st.download_button(
            label="📋 Download Text Report",
            data=text_report,
            file_name=f"nodal_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )

else:
    # No results yet - show instructions
    st.info("👆 Upload an IFC file above to begin compliance checking")
    
    with st.expander("ℹ️ About NODAL"):
        st.markdown("""
        **NODAL** is an automated compliance checker for Swedish BFS 2024:1 accessibility standards.
        
        **Currently checking:**
        - ✓ BFS 2024:1 Section 3:14 - 1500mm wheelchair turning circle
        - ✓ BFS 2024:1 Section 3:15 - 900mm minimum door width
        - ⚠ BFS 2024:1 Section 3:16 - 25mm maximum threshold height (placeholder)
        
        **How to use:**
        1. Upload your building model (IFC format)
        2. Click "Check Compliance"
        3. Review results and download reports
        
        **Supported file formats:**
        - IFC 4.0 (recommended)
        - IFC 2x3 (supported)
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.85rem; padding: 1rem;">
    NODAL - BFS 2024:1 Compliance Checker | Built for Swedish Construction Industry<br>
    <em>Ensuring accessibility compliance through automated geometric analysis</em>
</div>
""", unsafe_allow_html=True)