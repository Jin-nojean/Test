import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="GFI 계산기", layout="centered")

menu = st.sidebar.radio("계산 항목 선택", ["GFI 계산기", "FuelEU", "CII", "EU ETS"])

if menu == "GFI 계산기":
    st.title("🌱 GFI 계산기")

    if "fuel_data" not in st.session_state:
        st.session_state["fuel_data"] = []
    if "edit_index" not in st.session_state:
        st.session_state["edit_index"] = None

    if st.session_state["edit_index"] is not None:
        st.subheader("✏️ 연료 수정")
        edit_row = st.session_state.fuel_data[st.session_state["edit_index"]]
        with st.form("edit_form"):
            fuel_type = st.selectbox("연료 종류", ["VLSFO", "HSFO", "LSMGO", "LNG", "B24", "B30", "B100"],
                                     index=["VLSFO", "HSFO", "LSMGO", "LNG", "B24", "B30", "B100"].index(edit_row["연료종류"]))
            lhv = st.number_input("저위발열량 (MJ/Ton)", value=edit_row["LHV"], min_value=0.0)
            wtw = st.number_input("Well-to-Wake 계수 (gCO₂eq/MJ)", value=edit_row["WtW"], min_value=0.0)
            amount = st.number_input("사용량 (톤)", value=edit_row["사용량"], min_value=0.0)
            submitted = st.form_submit_button("수정 완료")
            if submitted:
                st.session_state.fuel_data[st.session_state["edit_index"]] = {
                    "연료종류": fuel_type,
                    "LHV": lhv,
                    "WtW": wtw,
                    "사용량": amount
                }
                st.session_state["edit_index"] = None
                st.rerun()
    else:
        st.subheader("➕ 연료 추가")
        with st.form("fuel_form"):
            fuel_type = st.selectbox("연료 종류", ["VLSFO", "HSFO", "LSMGO", "LNG", "B24", "B30", "B100"])
            lhv = st.number_input("저위발열량 (MJ/Ton)", min_value=0.0)
            wtw = st.number_input("Well-to-Wake 계수 (gCO₂eq/MJ)", min_value=0.0)
            amount = st.number_input("사용량 (톤)", min_value=0.0)
            submitted = st.form_submit_button("연료 추가")
            if submitted:
                st.session_state.fuel_data.append({
                    "연료종류": fuel_type,
                    "LHV": lhv,
                    "WtW": wtw,
                    "사용량": amount
                })
                st.rerun()

    st.divider()
    st.subheader("📋 입력한 연료 목록")

    delete_indices = []
    for i, row in enumerate(st.session_state.fuel_data, start=1):
        cols = st.columns([0.5, 1, 2, 2, 2, 2, 1])
        with cols[0]:
            selected = st.checkbox("", key=f"check_{i}")
        with cols[1]:
            st.write(f"{i}")
        with cols[2]:
            st.write(row["연료종류"])
        with cols[3]:
            st.write(row["LHV"])
        with cols[4]:
            st.write(row["WtW"])
        with cols[5]:
            st.write(row["사용량"])
        with cols[6]:
            if st.button("✏️", key=f"edit_{i}"):
                st.session_state["edit_index"] = i - 1
                st.rerun()
        if selected:
            delete_indices.append(i - 1)

    if delete_indices:
        if st.button("🗑️ 선택한 연료 삭제"):
            for index in sorted(delete_indices, reverse=True):
                st.session_state.fuel_data.pop(index)
            st.session_state["edit_index"] = None
            st.rerun()

    if st.button("GFI 계산하기"):
        df = pd.DataFrame(st.session_state.fuel_data)
        if not df.empty:
            df["총배출량(kg)"] = df["LHV"] * df["WtW"] * df["사용량"] * 1e-3
            df["총에너지(MJ)"] = df["LHV"] * df["사용량"]
            total_emission = df["총배출량(kg)"].sum()
            total_energy = df["총에너지(MJ)"].sum()
            gfi = (total_emission * 1000) / total_energy
            st.success(f"계산된 GFI: **{gfi:.2f} gCO₂eq/MJ**")

            years = list(range(2028, 2036))
            base_gfi = [round(93.3 * r, 5) for r in [0.96, 0.94, 0.92, 0.877, 0.832, 0.788, 0.744, 0.7]]
            direct_gfi = [93.3*(1-0.17),93.3*(1-0.19),93.3*(1-0.21),93.3*(1-0.254),93.3*(1-0.298),93.3*(1-0.342),93.3*(1-0.386),93.3*(1-0.43)]

            # 그래프 시각화
            plt.figure(figsize=(8, 4))
            plt.plot(years, base_gfi, label="Base GFI", linestyle="--", marker="o")
            plt.plot(years, direct_gfi, label="Direct GFI", linestyle=":", marker="o")
            plt.hlines(gfi, 2028, 2035, color="red", linestyles="-", label=f"Your GFI: {gfi:.2f}")
            for x, y in zip(years, base_gfi):
                plt.text(x, y + 1, f"{y:.1f}", ha='center', va='bottom', fontsize=8)
            for x, y in zip(years, direct_gfi):
                plt.text(x, y + 1, f"{y:.1f}", ha='center', va='bottom', fontsize=8)
            plt.xlabel("연도")
            plt.ylabel("gCO₂eq/MJ")
            plt.title("GFI vs 기준 GFI")
            plt.legend()
            st.pyplot(plt)

            # Compliance 결과 테이블
            data = []
            surplus_data = []
            for i, (y, bg, dg) in enumerate(zip(years, base_gfi, direct_gfi), start=1):
                row = {"No.": i, "연도": y}
                total_penalty = 0

                if gfi > bg:
                    row["Tier"] = "Tier 2"
                    cb1 = round(round(bg - dg, 5) * round(total_energy, 2) / 1e6, 2)
                    cb2 = round(round(gfi - bg, 5) * round(total_energy, 2) / 1e6, 2)
                    p1 = round(cb1 * 100, 0)
                    p2 = round(cb2 * 380, 1)
                    total_penalty = p1 + p2
                    row["Tier 1 CB (tCO₂eq)"] = f"{cb1:,.2f} tCO₂eq"
                    row["Tier 2 CB (tCO₂eq)"] = f"{cb2:,.2f} tCO₂eq"
                    row["Tier 1 Penalty ($)"] = f"${p1:,.0f}"
                    row["Tier 2 Penalty ($)"] = f"${p2:,.1f}"

                elif gfi > dg:
                    row["Tier"] = "Tier 1"
                    cb1 = round(round(gfi - dg, 5) * round(total_energy, 2) / 1e6, 2)
                    p1 = round(cb1 * 100, 0)
                    total_penalty = p1
                    row["Tier 1 CB (tCO₂eq)"] = f"{cb1:,.2f} tCO₂eq"
                    row["Tier 1 Penalty ($)"] = f"${p1:,.0f}"

                else:
                    row["Tier"] = "Surplus"
                    surplus = round(round(dg - gfi, 5) * round(total_energy, 2) / 1e6, 2)
                    row["Surplus (tCO₂eq)"] = f"{surplus:,.2f} tCO₂eq"
                    surplus_data.append({"연도": y, "Surplus (tCO₂eq)": f"{surplus:,.2f} tCO₂eq"})

                if row["Tier"] != "Surplus":
                    row["Total Penalty ($)"] = f"${total_penalty:,.1f}"
                else:
                    row["Total Penalty ($)"] = "None"

                data.append(row)

            st.subheader("📘 연도별 Compliance 결과")
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

            if surplus_data:
                st.subheader("🟢 Surplus 발생 연도")
                st.dataframe(pd.DataFrame(surplus_data), use_container_width=True, hide_index=True)
        else:
            st.warning("먼저 연료를 입력해주세요.")

elif menu == "FuelEU":
    st.title("🚢 FuelEU Maritime 계산기 (준비 중)")
elif menu == "CII":
    st.title("⚓ CII 계산기 (준비 중)")
elif menu == "EU ETS":
    st.title("💶 EU ETS 계산기 (준비 중)")



