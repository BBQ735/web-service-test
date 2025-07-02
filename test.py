import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
import re

st.set_page_config(page_title="Step-by-step Measurement Input", layout="centered")

NUM_FEATURES = 3
MAX_MEASURE = 30

if "feature_data" not in st.session_state:
    st.session_state.feature_data = [
        {
            "name": f"Feature {i+1}",
            "usl": None,
            "lsl": None,
            "values": [""]
        } for i in range(NUM_FEATURES)
    ]

st.title("📏 Step-by-step Measurement Input Tool (No +/-, Add row by button)")

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
            usl_str = st.text_input(
                "USL", value="" if feature["usl"] is None else str(feature["usl"]), key=f"usl_{idx}"
            )
            feature["usl"] = float(usl_str) if re.match(r'^-?\d+(\.\d+)?$', usl_str) else None
        with col2:
            lsl_str = st.text_input(
                "LSL", value="" if feature["lsl"] is None else str(feature["lsl"]), key=f"lsl_{idx}"
            )
            feature["lsl"] = float(lsl_str) if re.match(r'^-?\d+(\.\d+)?$', lsl_str) else None

        st.markdown("#### Measurement Values")
        values = feature["values"]

        for row in range(len(values)):
            input_cols = st.columns([1, 4])
            input_key = f"feat{idx}_val{row}"
            val = st.session_state.get(input_key, values[row])

            # 入力欄（text_inputで+/-非表示、数字のみ許容）
            input_val = input_cols[1].text_input(
                f"{feature['name']} #{row+1}",
                value=val,
                key=input_key,
                label_visibility="collapsed"
            )

            # 入力値を保存
            feature["values"][row] = input_val

            # 数値化できればOK/NG判定
            if input_val.strip() == "":
                input_cols[0].write("")
            elif not re.match(r'^-?\d+(\.\d+)?$', input_val):
                input_cols[0].markdown(
                    f"<span style='color:red;font-weight:bold'>Error</span>", unsafe_allow_html=True
                )
            else:
                num = float(input_val)
                ok = True
                if feature["usl"] is not None and num > feature["usl"]:
                    ok = False
                if feature["lsl"] is not None and num < feature["lsl"]:
                    ok = False
                judge = "OK" if ok else "NG"
                color = "green" if ok else "red"
                input_cols[0].markdown(
                    f"<span style='color:{color};font-weight:bold'>{judge}</span>", unsafe_allow_html=True
                )

        # --- +ボタンで新規入力欄追加 ---
        if len(values) < MAX_MEASURE:
            add_key = f"add_row_{idx}"
            if st.button("＋ Add Row", key=add_key):
                feature["values"].append("")

    st.info("No +/- on input. Click ＋ Add Row to add new input boxes. Enter only numbers.")

# ----------- STATISTICS TAB ---------------
with tab2:
    st.subheader("Statistics, Judgement, and Histogram")
    csv_buffers = []

    for idx, feature in enumerate(st.session_state.feature_data):
        # Only valid numeric entries
        valid_nums = []
        for v in feature["values"]:
            try:
                num = float(v)
                valid_nums.append(num)
            except:
                pass
        if len(valid_nums) == 0:
            continue

        df = pd.DataFrame({
            "No.": np.arange(1, len(valid_nums)+1),
            "Value": valid_nums,
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
        st.write(f"MAX: **{np.max(valid_nums):.3f}**")
        st.write(f"MIN: **{np.min(valid_nums):.3f}**")
        st.write(f"AVE: **{np.mean(valid_nums):.3f}**")
        std = np.std(valid_nums, ddof=1) if len(valid_nums) > 1 else 0
        st.write(f"Std. Dev.: **{std:.3f}**")
        if std > 0:
            if usl is not None and lsl is not None:
                cp = (usl - lsl) / (6 * std)
                cpk = min((usl - np.mean(valid_nums)) / (3 * std), (np.mean(valid_nums) - lsl) / (3 * std))
                st.write(f"Cp: **{cp:.3f}**　Cpk: **{cpk:.3f}** (Both-side)")
            elif usl is not None:
                cpk = (usl - np.mean(valid_nums)) / (3 * std)
                st.write(f"Cpk (USL only): **{cpk:.3f}**")
            elif lsl is not None:
                cpk = (np.mean(valid_nums) - lsl) / (3 * std)
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
