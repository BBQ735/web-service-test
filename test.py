import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Step-by-step Measurement Input", layout="centered")

NUM_FEATURES = 3
MAX_MEASURE = 30

if "feature_data" not in st.session_state:
    st.session_state.feature_data = [
        {
            "name": f"Feature {i+1}",
            "usl": None,
            "lsl": None,
            "values": []
        } for i in range(NUM_FEATURES)
    ]

st.title("📏 Step-by-step Measurement Input Tool")
tab1, tab2 = st.tabs(["Input", "Statistics & Chart"])

with tab1:
    product_no = st.text_input("Product No.", placeholder="e.g. ABC123")
    lot_no = st.text_input("Lot No.", placeholder="e.g. L20240701")

    for idx, feature in enumerate(st.session_state.feature_data):
        st.markdown(f"---\n### {feature['name']}")
        feature["name"] = st.text_input(
            f"Feature {idx+1} Name", value=feature["name"], key=f"name_{idx}")
        col1, col2 = st.columns(2)
        with col1:
            feature["usl"] = st.number_input(
                "USL", value=feature["usl"], step=0.001, format="%.3f", key=f"usl_{idx}")
        with col2:
            feature["lsl"] = st.number_input(
                "LSL", value=feature["lsl"], step=0.001, format="%.3f", key=f"lsl_{idx}")

        st.markdown("#### Measurement Values")

        # 入力欄のロジック
        values = feature["values"]
        max_input_len = len(values)
        if max_input_len == 0:
            values.append(None)
            max_input_len = 1

        for row in range(max_input_len):
            input_cols = st.columns([1, 4])
            v = values[row]
            val = input_cols[1].number_input(
                f"{feature['name']} #{row+1}", value=v, key=f"feat{idx}_val{row}", format="%.3f", step=0.001, label_visibility="collapsed"
            )
            feature["values"][row] = val

            # OK/NG判定
            judge = "-"
            if val is not None:
                ok = True
                if feature["usl"] is not None and val > feature["usl"]:
                    ok = False
                if feature["lsl"] is not None and val < feature["lsl"]:
                    ok = False
                judge = "OK" if ok else "NG"
                color = "green" if ok else "red"
                input_cols[0].markdown(
                    f"<span style='color:{color};font-weight:bold'>{judge}</span>",
                    unsafe_allow_html=True
                )
            else:
                input_cols[0].write("")

        # 新規欄を自動追加
        if (values and values[-1] is not None) and len(values) < MAX_MEASURE:
            feature["values"].append(None)

    st.info("Each feature's measurement values and OK/NG are grouped together for easy input, even on smartphones.")

# ----------- STATISTICS TAB ---------------
with tab2:
    st.subheader("Statistics, Judgement, and Histogram")
    csv_buffers = []

    for idx, feature in enumerate(st.session_state.feature_data):
        values = [v for v in feature["values"] if v is not None]
        if len(values) == 0:
            continue

        df = pd.DataFrame({
            "No.": np.arange(1, len(values)+1),
            "Value": values,
        })
        usl = feature["usl"]
        lsl = feature["lsl"]

        def judge(x):
            if usl is not None and lsl is not None:
                return "OK" if lsl <= x <= usl else "NG"
            elif usl is not None:
                return "OK" if x <= usl else "NG"
            elif lsl is not None:
                return "OK" if x >= lsl else "NG"
            else:
                return "-"
        df["Result"] = df["Value"].apply(judge)

        st.markdown(f"### {feature['name']}")
        st.write(f"MAX: **{np.max(values):.3f}**")
        st.write(f"MIN: **{np.min(values):.3f}**")
        st.write(f"AVE: **{np.mean(values):.3f}**")
        std = np.std(values, ddof=1) if len(values) > 1 else 0
        st.write(f"Std. Dev.: **{std:.3f}**")
        if std > 0:
            if usl is not None and lsl is not None:
                cp = (usl - lsl) / (6 * std)
                cpk = min((usl - np.mean(values)) / (3 * std), (np.mean(values) - lsl) / (3 * std))
                st.write(f"Cp: **{cp:.3f}**　Cpk: **{cpk:.3f}** (Both-side)")
            elif usl is not None:
                cpk = (usl - np.mean(values)) / (3 * std)
                st.write(f"Cpk (USL only): **{cpk:.3f}**")
            elif lsl is not None:
                cpk = (np.mean(values) - lsl) / (3 * std)
                st.write(f"Cpk (LSL only): **{cpk:.3f}**")
        else:
            st.write("Cp/Cpk cannot be calculated (Std.Dev=0 or single value).")

        def highlight_ng(row):
            return [
                'background-color: #ffcccc' if col == 'Result' and row['Result'] == 'NG' else ''
                for col in row.index
            ]

        st.dataframe(
            df.style.apply(highlight_ng, axis=1),
            hide_index=True, use_container_width=True
        )

        st.subheader("Histogram")
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.hist(df["Value"], bins=10, edgecolor="black")
        ax.set_xlabel("Value")
        ax.set_ylabel("Frequency")
        if usl is not None:
            ax.axvline(usl, color="red", linestyle="--", label="USL")
        if lsl is not None:
            ax.axvline(lsl, color="red", linestyle="--", label="LSL")
        ax.legend()
        st.pyplot(fig)

        out = io.StringIO()
        export_df = df[["No.", "Value", "Result"]]
        export_df.to_csv(out, index=False, encoding="utf-8-sig")
        csv_buffers.append((feature["name"], out.getvalue()))

    if csv_buffers:
        st.subheader("CSV Export (for each feature)")
        for featname, buf in csv_buffers:
            st.download_button(
                label=f"Download {featname} as CSV",
                data=buf,
                file_name=f"{product_no or 'data'}_{lot_no or ''}_{featname}.csv",
                mime='text/csv'
            )
