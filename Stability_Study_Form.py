import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Stability Sample Generator", layout="centered")

# Custom CSS for sans-serif font
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# Controlled Vocabulary
VOCAB = {
    "storage_temp": ["-70°C", "-50°C", "-30°C", "≤-30°C", "-20°C", "2-8°C", "4°C", "5°C", "25°C", "30°C", "40°C", "LN2",
                     "RT"],
    "ds_temperature": ["-70°C", "-70°C w/5day 30°C", "-50°C", "-50°C w/5day 30°C", "2-8°C", "25°C"],
    "vial_orientation": ["upright", "inverted"],
    "transportation": ["Control", "Transport Rep 1", "Transport Rep 2", "Transport Rep 3"],
    "time_units": ["week", "month", "year"]
}

# Initialize session state
if 'samples' not in st.session_state:
    st.session_state.samples = []


def clear_all():
    """Clear all session data"""
    st.session_state.samples = []
    for key in list(st.session_state.keys()):
        if key != 'samples':
            del st.session_state[key]


def create_sample_record(exp_id, molecule, source, formulation, parent, create_date,
                         conc, label, micro_label, time_pt, time_unit, temp, temp_ds,
                         vial_o, transport, freeze_thaw):
    """Create a single sample record matching LabKey format"""
    description = f"{molecule} {source}, {formulation}, {conc} mg/mL, {micro_label} {vial_o}".strip()
    label_text = f"{molecule} {source}, {formulation}, {conc} mg/mL, {micro_label} {vial_o}".strip()

    return {
        "Parent": parent,
        "Description": description,
        "Label": label_text,
        "Micro Label": micro_label,
        "Sample Date": create_date,
        "Time Point": time_pt,
        "Time Point Units": time_unit,
        "Conc. (mg/mL)": conc,
        "Storage Temp": temp,
        "DS Temperature": temp_ds,
        "Formulation": formulation,
        "Experiment Id": exp_id,
        "Storage Vial Orientation Conditions": vial_o,
        "Transportation": transport,
        "Stability Freeze Thaw Count": freeze_thaw
    }


def generate_stability_samples(exp_id, molecule, source, parent, create_date, conc,
                               formulation, formulation_parent, formulation_conc,
                               time_points, time_units, temperatures, vial_orientations,
                               matrix, extra_vials, study_type="DP"):
    """Generate stability study samples based on matrix"""
    samples = []

    # Use formulation-specific values if provided
    prnt = formulation_parent if formulation_parent else parent
    cnc = formulation_conc if formulation_conc else conc

    # T0 sample
    t0_label = "t0" if study_type == "DP" else "t0, DS"
    t0_time_unit = time_units[0] if time_units and time_units[0] else ""
    samples.append(create_sample_record(
        exp_id, molecule, source, formulation, prnt, create_date, cnc,
        t0_label, t0_label, 0, t0_time_unit,
        "", "", "", "", ""
    ))

    # Time point samples
    for i, time_pt in enumerate(time_points):
        if not time_pt:
            continue
        time_unit = time_units[i] if i < len(time_units) else ""

        for j, temp in enumerate(temperatures):
            if not temp:
                continue

            # Check if this combination is marked in matrix
            if i < len(matrix) and j < len(matrix[i]) and matrix[i][j]:
                vial_o = vial_orientations[j] if j < len(vial_orientations) else ""

                # Create label
                if time_unit == "week":
                    suffix = "w"
                elif time_unit == "month":
                    suffix = "m"
                elif time_unit == "year":
                    suffix = "y"
                else:
                    suffix = ""

                if study_type == "DP":
                    micro_label = f"{temp}, {time_pt}{suffix}"
                else:  # DS
                    micro_label = f"{temp}, {time_pt}{suffix} DS"

                temp_field = temp if study_type == "DP" else ""
                temp_ds_field = temp if study_type == "DS" else ""

                samples.append(create_sample_record(
                    exp_id, molecule, source, formulation, prnt, create_date, cnc,
                    micro_label, micro_label, time_pt, time_unit, temp_field, temp_ds_field,
                    vial_o, "", ""
                ))

    # Extra vials
    for j, temp in enumerate(temperatures):
        if not temp:
            continue
        extra_count = extra_vials[j] if j < len(extra_vials) else 0
        vial_o = vial_orientations[j] if j < len(vial_orientations) else ""

        for k in range(int(extra_count)):
            micro_label = f"{temp}, extra{k + 1}"
            temp_field = temp if study_type == "DP" else ""
            temp_ds_field = temp if study_type == "DS" else ""

            samples.append(create_sample_record(
                exp_id, molecule, source, formulation, prnt, create_date, cnc,
                micro_label, micro_label, "", "", temp_field, temp_ds_field,
                vial_o, "", ""
            ))

    return samples


# Header
st.title("Stability SampleID Generator v1.0")
st.markdown("Generate sample lists for LabKey LIMS upload")

# Overall Study Information
st.header("Study Information")
col1, col2, col3 = st.columns(3)

with col1:
    exp_id = st.text_input("Experiment ID*", value="", key="exp_id")
    molecule = st.text_input("Molecule*", value="", key="molecule")
    source = st.text_input("Source*", value="", key="source")

with col2:
    parent = st.text_input("Parent Sample ID*", value="", key="parent")
    create_date = st.date_input("Sample Creation Date*", value=datetime.now(), key="create_date")
    t0_date = st.date_input("T0 Date", value=datetime.now(), key="t0_date")

with col3:
    concentration = st.number_input("Default Concentration (mg/mL)*", min_value=0.0, value=100.0, step=0.1,
                                    key="concentration")

# Tabs for different study types
tab1, tab2, tab3, tab4 = st.tabs(["📊 DP Stability", "🧫 DS Stability", "❄️ Freeze/Thaw", "🚚 Transportation"])

# DP STABILITY TAB
with tab1:
    st.subheader("Drug Product Stability Study")

    default_dp_forms = 1
    default_dp_temps = 3
    default_dp_times = 5

    # Formulations
    st.markdown("**Formulations**")
    num_dp_forms = st.number_input("Number of DP Formulations", min_value=1, max_value=12, value=default_dp_forms,
                                   key="num_dp_forms")

    dp_formulations = []
    for i in range(num_dp_forms):
        col1, col2, col3 = st.columns(3)
        with col1:
            form = st.text_input(f"Formulation {i + 1}", key=f"dp_form_{i}")
        with col2:
            form_parent = st.text_input(f"Parent (optional)", key=f"dp_parent_{i}", placeholder="Uses default")
        with col3:
            form_conc = st.number_input(f"Conc. (optional)", key=f"dp_conc_{i}", min_value=0.0, value=0.0, step=0.1)

        if form:
            dp_formulations.append({
                'formulation': form,
                'parent': form_parent,
                'concentration': form_conc if form_conc > 0 else None
            })

    # Temperatures
    st.markdown("**Storage Conditions**")
    num_dp_temps = st.number_input("Number of Temperature Conditions", min_value=1, max_value=8, value=default_dp_temps,
                                   key="num_dp_temps")

    preset_temps = ["-20°C", "2-8°C", "25°C"]

    dp_temps = []
    dp_vials = []
    dp_extras = []

    cols = st.columns(num_dp_temps)
    for i, col in enumerate(cols):
        with col:
            default_temp = preset_temps[i] if i < len(preset_temps) else VOCAB["storage_temp"][0]
            temp = st.selectbox(f"Temp {i + 1}", options=VOCAB["storage_temp"],
                                index=VOCAB["storage_temp"].index(default_temp) if default_temp in VOCAB[
                                    "storage_temp"] else 0,
                                key=f"dp_temp_{i}")
            vial = st.selectbox(f"Vial Orient.", options=[""] + VOCAB["vial_orientation"], key=f"dp_vial_{i}")
            extra = st.number_input(f"Extra Vials", key=f"dp_extra_{i}", min_value=0, max_value=10, value=0)
            dp_temps.append(temp)
            dp_vials.append(vial)
            dp_extras.append(extra)

    # Time Points
    st.markdown("**Time Points**")
    num_dp_times = st.number_input("Number of Time Points", min_value=1, max_value=20, value=default_dp_times,
                                   key="num_dp_times")

    dp_times = []
    dp_units = []
    dp_matrix = []

    for i in range(num_dp_times):
        col1, col2 = st.columns([1, 3])
        with col1:
            time_val = st.number_input(f"Time {i + 1}", key=f"dp_time_{i}", min_value=0.0, value=0.0, step=0.5)
            time_unit = st.selectbox(f"Unit", options=VOCAB["time_units"], key=f"dp_unit_{i}")
        with col2:
            st.markdown(f"**Select temps for time point {i + 1}:**")
            checks = st.columns(num_dp_temps)
            matrix_row = []
            for j, check_col in enumerate(checks):
                with check_col:
                    checked = st.checkbox(f"{dp_temps[j][:15]}", key=f"dp_matrix_{i}_{j}", value=False)
                    matrix_row.append(checked)
            dp_matrix.append(matrix_row)

        dp_times.append(time_val)
        dp_units.append(time_unit)

    if st.button("🧬 Generate DP Samples", type="primary"):
        if not all([exp_id, molecule, source, parent]):
            st.error("Please fill in all required study information fields")
        elif not dp_formulations:
            st.error("Please add at least one formulation")
        else:
            for form_data in dp_formulations:
                samples = generate_stability_samples(
                    exp_id, molecule, source, parent, create_date.strftime("%Y-%m-%d"),
                    concentration, form_data['formulation'], form_data['parent'],
                    form_data['concentration'], dp_times, dp_units, dp_temps,
                    dp_vials, dp_matrix, dp_extras, "DP"
                )
                st.session_state.samples.extend(samples)
            st.success(
                f"✅ Generated {sum(len(generate_stability_samples(exp_id, molecule, source, parent, create_date.strftime('%Y-%m-%d'), concentration, fd['formulation'], fd['parent'], fd['concentration'], dp_times, dp_units, dp_temps, dp_vials, dp_matrix, dp_extras, 'DP')) for fd in dp_formulations)} DP samples!")
            st.rerun()

# DS STABILITY TAB
with tab2:
    st.subheader("Drug Substance Stability Study")

    default_ds_forms = 1
    default_ds_temps = 2
    default_ds_times = 3

    num_ds_forms = st.number_input("Number of DS Formulations", min_value=1, max_value=12, value=default_ds_forms,
                                   key="num_ds_forms")

    ds_formulations = []
    for i in range(num_ds_forms):
        col1, col2, col3 = st.columns(3)
        with col1:
            form = st.text_input(f"DS Formulation {i + 1}", key=f"ds_form_{i}")
        with col2:
            form_parent = st.text_input(f"DS Parent (optional)", key=f"ds_parent_{i}", placeholder="Uses default")
        with col3:
            form_conc = st.number_input(f"DS Conc. (optional)", key=f"ds_conc_{i}", min_value=0.0, value=0.0, step=0.1)

        if form:
            ds_formulations.append({
                'formulation': form,
                'parent': form_parent,
                'concentration': form_conc if form_conc > 0 else None
            })

    # DS Temperatures
    num_ds_temps = st.number_input("Number of DS Temperature Conditions", min_value=1, max_value=8,
                                   value=default_ds_temps, key="num_ds_temps")

    ds_temps = []
    ds_extras = []

    cols = st.columns(num_ds_temps)
    for i, col in enumerate(cols):
        with col:
            temp = st.selectbox(f"DS Temp {i + 1}", options=VOCAB["ds_temperature"], key=f"ds_temp_{i}")
            extra = st.number_input(f"Extra Bags", key=f"ds_extra_{i}", min_value=0, max_value=10, value=0)
            ds_temps.append(temp)
            ds_extras.append(extra)

    # DS Time Points
    num_ds_times = st.number_input("Number of DS Time Points", min_value=1, max_value=14, value=default_ds_times,
                                   key="num_ds_times")

    ds_times = []
    ds_units = []
    ds_matrix = []

    for i in range(num_ds_times):
        col1, col2 = st.columns([1, 3])
        with col1:
            time_val = st.number_input(f"DS Time {i + 1}", key=f"ds_time_{i}", min_value=0.0, value=0.0, step=0.5)
            time_unit = st.selectbox(f"DS Unit", options=VOCAB["time_units"], key=f"ds_unit_{i}")
        with col2:
            st.markdown(f"**Select DS temps for time point {i + 1}:**")
            checks = st.columns(num_ds_temps)
            matrix_row = []
            for j, check_col in enumerate(checks):
                with check_col:
                    checked = st.checkbox(f"{ds_temps[j][:20]}", key=f"ds_matrix_{i}_{j}", value=False)
                    matrix_row.append(checked)
            ds_matrix.append(matrix_row)

        ds_times.append(time_val)
        ds_units.append(time_unit)

    if st.button("🧬 Generate DS Samples", type="primary"):
        if not all([exp_id, molecule, source, parent]):
            st.error("Please fill in all required study information fields")
        elif not ds_formulations:
            st.error("Please add at least one DS formulation")
        else:
            for form_data in ds_formulations:
                samples = generate_stability_samples(
                    exp_id, molecule, source, parent, create_date.strftime("%Y-%m-%d"),
                    concentration, form_data['formulation'], form_data['parent'],
                    form_data['concentration'], ds_times, ds_units, ds_temps,
                    [], ds_matrix, ds_extras, "DS"
                )
                st.session_state.samples.extend(samples)
            st.success(f"✅ Generated DS samples!")
            st.rerun()

# FREEZE/THAW TAB
with tab3:
    st.subheader("Freeze/Thaw Study")

    default_ft_forms = 1
    default_cycles = 4

    num_ft_forms = st.number_input("Number of F/T Formulations", min_value=1, max_value=12, value=default_ft_forms,
                                   key="num_ft_forms")

    ft_formulations = []
    for i in range(num_ft_forms):
        col1, col2, col3 = st.columns(3)
        with col1:
            form = st.text_input(f"F/T Formulation {i + 1}", key=f"ft_form_{i}")
        with col2:
            form_parent = st.text_input(f"F/T Parent (optional)", key=f"ft_parent_{i}", placeholder="Uses default")
        with col3:
            form_conc = st.number_input(f"F/T Conc. (optional)", key=f"ft_conc_{i}", min_value=0.0, value=0.0, step=0.1)

        if form:
            ft_formulations.append({
                'formulation': form,
                'parent': form_parent,
                'concentration': form_conc if form_conc > 0 else None
            })

    st.markdown("**Freeze/Thaw Cycles**")
    num_cycles = st.number_input("Number of Cycle Conditions", min_value=1, max_value=10, value=default_cycles,
                                 key="num_cycles")

    ft_cycles = []
    cols = st.columns(min(num_cycles, 4))
    for i in range(num_cycles):
        with cols[i % 4]:
            cycle = st.number_input(f"Cycles {i + 1}", key=f"ft_cycle_{i}", min_value=1, max_value=20, value=i + 1)
            include = st.checkbox(f"Include", key=f"ft_include_{i}", value=True)
            if include:
                ft_cycles.append(cycle)

    if st.button("❄️ Generate F/T Samples", type="primary"):
        if not all([exp_id, molecule, source, parent]):
            st.error("Please fill in all required study information fields")
        elif not ft_formulations or not ft_cycles:
            st.error("Please add formulations and cycles")
        else:
            for form_data in ft_formulations:
                prnt = form_data['parent'] if form_data['parent'] else parent
                cnc = form_data['concentration'] if form_data['concentration'] else concentration

                for cycle in ft_cycles:
                    micro_label = f"{cycle}X FT"
                    sample = create_sample_record(
                        exp_id, molecule, source, form_data['formulation'], prnt,
                        create_date.strftime("%Y-%m-%d"), cnc, micro_label, micro_label,
                        "", "", "", "", "", "", str(cycle)
                    )
                    st.session_state.samples.append(sample)

            st.success(f"✅ Generated {len(ft_formulations) * len(ft_cycles)} F/T samples!")
            st.rerun()

# TRANSPORTATION TAB
with tab4:
    st.subheader("Transportation Study")

    default_tr_forms = 1
    default_surfs = 0

    num_tr_forms = st.number_input("Number of Base Formulations", min_value=1, max_value=12, value=default_tr_forms,
                                   key="num_tr_forms")

    tr_formulations = []
    for i in range(num_tr_forms):
        col1, col2, col3 = st.columns(3)
        with col1:
            form = st.text_input(f"Base Formulation {i + 1}", key=f"tr_form_{i}")
        with col2:
            form_parent = st.text_input(f"Trans Parent (optional)", key=f"tr_parent_{i}", placeholder="Uses default")
        with col3:
            form_conc = st.number_input(f"Trans Conc. (optional)", key=f"tr_conc_{i}", min_value=0.0, value=0.0,
                                        step=0.1)

        if form:
            tr_formulations.append({
                'formulation': form,
                'parent': form_parent,
                'concentration': form_conc if form_conc > 0 else None
            })

    st.markdown("**Surfactants (Optional)**")
    num_surfs = st.number_input("Number of Surfactants", min_value=0, max_value=10, value=default_surfs,
                                key="num_surfs")

    surfactants = []
    if num_surfs > 0:
        cols = st.columns(min(num_surfs, 4))
        for i in range(num_surfs):
            with cols[i % 4]:
                surf = st.text_input(f"Surfactant {i + 1}", key=f"surf_{i}")
                if surf:
                    surfactants.append(surf)

    if st.button("🚚 Generate Transportation Samples", type="primary"):
        if not all([exp_id, molecule, source, parent]):
            st.error("Please fill in all required study information fields")
        elif not tr_formulations:
            st.error("Please add at least one formulation")
        else:
            for form_data in tr_formulations:
                prnt = form_data['parent'] if form_data['parent'] else parent
                cnc = form_data['concentration'] if form_data['concentration'] else concentration

                # Base formulation samples
                for transport_label in VOCAB["transportation"]:
                    micro_map = {"Control": "ctrl", "Transport Rep 1": "trans1",
                                 "Transport Rep 2": "trans2", "Transport Rep 3": "trans3"}
                    micro = micro_map[transport_label]

                    sample = create_sample_record(
                        exp_id, molecule, source, form_data['formulation'], prnt,
                        create_date.strftime("%Y-%m-%d"), cnc, transport_label, micro,
                        "", "", "", "", "", transport_label, ""
                    )
                    st.session_state.samples.append(sample)

                # Surfactant variants
                for surf in surfactants:
                    full_form = form_data['formulation'] + surf
                    for transport_label in VOCAB["transportation"]:
                        micro_map = {"Control": "ctrl", "Transport Rep 1": "trans1",
                                     "Transport Rep 2": "trans2", "Transport Rep 3": "trans3"}
                        micro = micro_map[transport_label]

                        sample = create_sample_record(
                            exp_id, molecule, source, full_form, prnt,
                            create_date.strftime("%Y-%m-%d"), cnc, transport_label, micro,
                            "", "", "", "", "", transport_label, ""
                        )
                        st.session_state.samples.append(sample)

            st.success(f"✅ Generated transportation samples!")
            st.rerun()

# Display generated samples
if st.session_state.samples:
    st.header("Generated Samples")
    df = pd.DataFrame(st.session_state.samples)
    st.dataframe(df, use_container_width=True, height=400)

    st.metric("Total Samples", len(df))

    # Excel Export
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Samples')
    excel_data = excel_buffer.getvalue()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    st.download_button(
        label="📊 Download Excel",
        data=excel_data,
        file_name=f"stability_samples_{exp_id}_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

else:
    st.info("👆 Fill in study information and generate samples from the tabs above")

st.markdown("---")

# Clear button at the bottom
if st.button("🗑️ Clear All Data", use_container_width=True, type="secondary"):
    clear_all()
    st.rerun()

st.markdown("*Generated samples will appear above for review before download*")