#완성
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

st.set_page_config(page_title="GFI & FuelEU 계산기", layout="centered")

# 메뉴
menu = st.sidebar.radio("계산 항목 선택", ["GFI 계산기(IMO 중기조치)", "FuelEU Maritime"])
#menu = st.sidebar.radio("계산 항목 선택", ["GFI 계산기", "FuelEU Maritime", "CII (준비 중)", "EU ETS (준비 중)"])

#GFI 계산기용 GFI 연료 기본값 생성 함수 -> B24,B30 연료 wtw, lcv 포함
def generate_GFI_fuel_defaults():
    # GFI 계산기용 GWP 값 / FeulEU Maritime 값 사용
    GFI_gwp_factors = {
        "CO2": 1,
        "CH4": 25,
        "N2O": 298
    }
    # GFI 계산기용 TtW 계수 / MEPC80차 기준
    GFI_ttw_factors = {
        "VLSFO": {"CO2": 3.114, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0402, "SLIP": 0, "RWD": 0, "CO2_slip": 0, "CH4_slip": 0, "N2O_slip": 0},
        "HSFO": {"CO2": 3.114, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0402, "SLIP": 0, "RWD": 0, "CO2_slip": 0, "CH4_slip": 0, "N2O_slip": 0},
        "LSMGO": {"CO2": 3.206, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0427, "SLIP": 0, "RWD": 0, "CO2_slip": 0, "CH4_slip": 0, "N2O_slip": 0},
        "LNG": {"CO2": 2.75, "CH4": 0, "N2O": 0.00011, "LCV": 0.0480, "SLIP": 0.0015, "RWD": 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
        "LPG(Propane)": {"CO2": 3.0, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0463, "SLIP": 0, "RWD": 0, "CO2_slip": 0, "CH4_slip": 0, "N2O_slip": 0},
        "LPG(Butane)": {"CO2": 3.03, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0457, "SLIP": 0, "RWD": 0, "CO2_slip": 0, "CH4_slip": 0, "N2O_slip": 0},
        "Bio(Fame)": {"CO2": 2.834, "CH4": 0, "N2O": 0, "LCV": 0.0372, "SLIP": 0, "RWD": 0, "CO2_slip": 0, "CH4_slip": 0, "N2O_slip": 0} #바이오디젤은 RED II 기준 / 아직 안나왔으니
    }
    # GFI 계산기용 WtT 계수
    GFI_wtt_factors = {
        "VLSFO": 16.8,
        "HSFO": 14.9,
        "LSMGO": 17.7,
        "LNG": 18.5,#LNG는 RED II 기준 / 아직 안나왔으니
        "LPG(Propane)": 7.8,#LPG는 RED II 기준 / 아직 안나왔으니
        "LPG(Butane)": 7.8,#LPG는 RED II 기준 / 아직 안나왔으니
        "Bio(Fame)": 20.8 - 2.834 / 0.0372# WtT값이 일단 안나옴
    }
    # GFI WtW 계수 함수 / 슬립 처리는 우선 FuelEU Maritime과 동일하게 사용
    def calculate_ttw(fuel_type: str) -> float:
        ttw = GFI_ttw_factors[fuel_type]
        gwp = GFI_gwp_factors
        LCV = ttw["LCV"]
        slip = ttw["SLIP"]

        if slip == 0:
            # 기본 연소 배출량
            co2eq = ttw["CO2"] * gwp["CO2"] + ttw["CH4"] * gwp["CH4"] + ttw["N2O"] * gwp["N2O"]
            return round(co2eq / LCV, 5)
        # Slip 처리
        elif slip > 0:
            combustion = (
            ttw["CO2"] * gwp["CO2"] + ttw["CH4"] * gwp["CH4"] + ttw["N2O"] * gwp["N2O"])
            # 슬립분
            slip_CO2 = ttw.get("CO2_slip", 0)
            slip_CH4 = ttw.get("CH4_slip", 0)
            slip_N2O = ttw.get("N2O_slip", 0)
            slip_emission = (slip_CO2 * gwp["CO2"] + slip_CH4 * gwp["CH4"] + slip_N2O * gwp["N2O"])
            total_emission = (1 - slip) * combustion + slip * slip_emission
            return round(total_emission / LCV, 5)
        else:
            raise ValueError(f"Unexpected slip value: {slip}")

    def calculate_wtw(fuel_type: str) -> float:
        return round(GFI_wtt_factors.get(fuel_type, 0) + calculate_ttw(fuel_type), 5)

    def calculate_mixed_fuel(fossil_name, bio_name, fossil_ratio, fuel_defaults_GFI):
        bio_ratio = 1 - fossil_ratio
        fossil_LHV = fuel_defaults_GFI[fossil_name]["LHV"]
        bio_LHV = fuel_defaults_GFI[bio_name]["LHV"]
        fossil_WtW = fuel_defaults_GFI[fossil_name]["WtW"]
        bio_WtW = fuel_defaults_GFI[bio_name]["WtW"]

        LHV_mix = fossil_LHV * fossil_ratio + bio_LHV * bio_ratio
        total_emission = fossil_WtW * fossil_LHV * fossil_ratio + bio_WtW * bio_LHV * bio_ratio
        WtW_mix = total_emission / LHV_mix

        return {"LHV": round(LHV_mix, 2), "WtW": round(WtW_mix, 8)}

    # 최종 연료 기본값 구성
    fuel_defaults = {}
    for fuel in GFI_ttw_factors:
        LCV = GFI_ttw_factors[fuel]["LCV"]
        LHV = round(LCV * 1_000_000, 0)
        WtW = calculate_wtw(fuel)
        fuel_defaults[fuel] = {"LHV": LHV, "WtW": WtW}

    fuel_defaults.update({
        "B24(HSFO)": calculate_mixed_fuel("HSFO", "Bio(Fame)", 0.76,fuel_defaults),
        "B30(HSFO)": calculate_mixed_fuel("HSFO", "Bio(Fame)", 0.7,fuel_defaults),
        "B24(VLSFO)": calculate_mixed_fuel("VLSFO", "Bio(Fame)", 0.76,fuel_defaults),
        "B30(VLSFO)": calculate_mixed_fuel("VLSFO", "Bio(Fame)", 0.7,fuel_defaults)
    })

    return fuel_defaults

# FuelEU Maritime용 연료 기본값 생성 함수 -> B24,B30 연료 wtw, lcv 포함
def generate_FEUM_fuel_defaults():
    # FuelEU Maritime용 GWP 값
    FEUM_gwp_factors = {
        "CO2": 1,
        "CH4": 25,
        "N2O": 298
    }

    # TtW 계수 (RED II)
    FEUM_ttw_factors = {
    # 📘 Annex II Fossil Fuels
    "HFO (Grades RME to RMK)": {"CO2": 3.114, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0405, "SLIP": 0.0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "LFO (Grades RMA to RMD)": {"CO2": 3.151, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0410, "SLIP": 0.0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "MDO MGO (Grades DMX to DMB)": {"CO2": 3.206, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0427, "SLIP": 0.0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "LNG / LNG Otto (dual fuel medium speed)": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0491, "SLIP": 0.031, "RWD": 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "LNG / LNG Otto (dual fuel slow speed)": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0491, "SLIP": 0.017, "RWD": 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "LNG / LNG Diesel (dual fuel slow speed)": {"CO2": 2.75, "CH4": 0, "N2O": 0.00011, "LCV": 0.0491, "SLIP": 0.002, "RWD": 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "LNG / LBSI": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0491, "SLIP": 0.026, "RWD": 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "Ethane": {"CO2": 2.927, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0464, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "LPG - Butane": {"CO2": 3.030, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0460, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "LPG - Propane": {"CO2": 3.000, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0460, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "H2 (natural gas) / Fuel Cells": {"CO2": 0.000, "CH4": 0.00000, "N2O": 0.00000, "LCV": 0.1200, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "H2 (natural gas) / ICE": {"CO2": 0.000, "CH4": 0.00000, "N2O": 0.00018, "LCV": 0.1200, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "NH3 (natural gas) / Fuel Cells": {"CO2": 0.000, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0186, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "NH3 (natural gas) / ICE": {"CO2": 0.000, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0180, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "Methanol (natural gas)": {"CO2": 1.375, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0199, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},

    # 📗 Annex II Biofuels
    "Bio-ethanol (wheat straw)": {"CO2": 1.913, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0270, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "Bio(Fame)": {"CO2": 2.834, "CH4": 0, "N2O": 0, "LCV": 0.0370, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "Hydrotreated Vegetable Oil (waste cooking oil)": {"CO2": 3.115, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0440, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "Liquefied Biomethane (bio-waste) / Otto (dual fuel medium speed)": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0500, "SLIP": 0.031,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "Liquefied Biomethane / Otto (dual fuel slow speed)": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0500, "SLIP": 0.017,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "Liquefied Biomethane / Diesel (dual fuels)": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0500, "SLIP": 0.002,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "Liquefied Biomethane / LBSI": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0500, "RWD" : 0,"SLIP": 0.026, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "Bio-methanol": {"CO2": 1.375, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0200, "SLIP": 0.0, "RWD" : 0,"CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "Other Production Pathways": {"CO2": 3.115, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0370, "SLIP": 0.0, "RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},

    # 📙 Annex II e-Fuels
    "e-diesel": {"CO2": 3.206, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0427, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "e-methanol": {"CO2": 1.375, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0199, "SLIP": 0.0,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "e-LNG / Otto (dual fuel medium speed)": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0491, "SLIP": 0.031,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "e-LNG / Otto (dual fuel slow speed)": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0491, "SLIP": 0.017,"RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "e-LNG / Diesel (dual fuel slow speed)": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0491, "SLIP": 0.002, "RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "e-LNG / LBSI": {"CO2": 2.750, "CH4": 0.00000, "N2O": 0.00011, "LCV": 0.0491, "SLIP": 0.026, "RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 1.0, "N2O_slip": 0.0},
    "e-H2 / Fuel Cells": {"CO2": 0.000, "CH4": 0.00000, "N2O": 0.00000, "LCV": 0.1200, "SLIP": 0.0, "RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "e-H2 / ICE": {"CO2": 0.000, "CH4": 0.00000, "N2O": 0.00018, "LCV": 0.1200, "SLIP": 0.0, "RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "e-NH3 / Fuel Cells": {"CO2": 0.000, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0186, "SLIP": 0.0, "RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0},
    "e-NH3 / ICE": {"CO2": 0.000, "CH4": 0.00005, "N2O": 0.00018, "LCV": 0.0186, "SLIP": 0.0, "RWD" : 0, "CO2_slip": 0.0, "CH4_slip": 0.0, "N2O_slip": 0.0}
}

    # WtT 계수 (RED II)
    FEUM_wtt_factors = {
        # 📘 Fossil Fuels (표 1)
        "HFO (Grades RME to RMK)": 13.5,
        "LFO (Grades RMA to RMD)": 13.2,
        "MDO MGO (Grades DMX to DMB)": 14.4,
        "LNG / LNG Otto (dual fuel medium speed)": 18.5,
        "LNG / LNG Otto (dual fuel slow speed)": 18.5,
        "LNG / LNG Diesel (dual fuel slow speed)": 18.5,
        "LNG / LBSI": 18.5,
        "Ethane": 18.5,
        "LPG - Butane": 7.8,
        "LPG - Propane": 7.8,
        "H2 (natural gas) / Fuel Cells": 132.0,
        "H2 (natural gas) / ICE": 132.0,
        "NH3 (natural gas) / Fuel Cells": 121.0,
        "NH3 (natural gas) / ICE": 121.0,
        "Methanol (natural gas)": 31.3,

        # 📗 Biofuels (표 2)
        "Bio-ethanol (wheat straw)": -55.15185,
        "Bio(Fame)": 14.6 - 2.834 / 0.037,
        "Hydrotreated Vegetable Oil (waste cooking oil)": -54.79545,
        "Liquefied Biomethane (bio-waste) / Otto (dual fuel medium speed)": -35.83000,
        "Liquefied Biomethane / Otto (dual fuel slow speed)": -35.83000,
        "Liquefied Biomethane / Diesel (dual fuels)": -35.83000,
        "Liquefied Biomethane / LBSI": -35.83000,
        "Bio-methanol": -58.35000,
        "Other Production Pathways": -69.18919,

        # 📙 e-Fuels (표 3)
        "e-diesel": -63.2,
        "e-methanol": -58.9,
        "e-LNG / Otto (dual fuel medium speed)": -46.2,
        "e-LNG / Otto (dual fuel slow speed)": -46.2,
        "e-LNG / Diesel (dual fuel slow speed)": -46.2,
        "e-LNG / LBSI": -46.2,
        "e-H2 / Fuel Cells": 10.0,
        "e-H2 / ICE": 10.0,
        "e-NH3 / Fuel Cells": 10.0,
        "e-NH3 / ICE": 10.0
    }


    def calculate_ttw(fuel_type: str) -> float:
        ttw = FEUM_ttw_factors[fuel_type]
        gwp = FEUM_gwp_factors
        LCV = ttw["LCV"]
        slip = ttw["SLIP"]

        if slip == 0:
            co2eq = ttw["CO2"] * gwp["CO2"] + ttw["CH4"] * gwp["CH4"] + ttw["N2O"] * gwp["N2O"]
            return round(co2eq / LCV, 15)
        elif slip > 0:
            combustion = ttw["CO2"] * gwp["CO2"] + ttw["CH4"] * gwp["CH4"] + ttw["N2O"] * gwp["N2O"]
            slip_CO2 = ttw.get("CO2_slip", 0)
            slip_CH4 = ttw.get("CH4_slip", 0)
            slip_N2O = ttw.get("N2O_slip", 0)
            slip_emission = (slip_CO2 * gwp["CO2"] + slip_CH4 * gwp["CH4"] + slip_N2O * gwp["N2O"])
            rwd = ttw.get("RWD", 0)
            total_emission = (1 - slip) * combustion + slip * slip_emission
            return round(total_emission / LCV, 15)
        else:
            raise ValueError(f"Unexpected slip value: {slip}")

    def calculate_wtw(fuel_type: str) -> float:
        return round(FEUM_wtt_factors.get(fuel_type, 0) + calculate_ttw(fuel_type), 15)

    def calculate_mixed_fuel(fossil_name, bio_name, fossil_ratio, fuel_defaults_FEUM):
        bio_ratio = 1 - fossil_ratio
        fossil_LHV = fuel_defaults_FEUM[fossil_name]["LHV"]
        bio_LHV = fuel_defaults_FEUM[bio_name]["LHV"]
        fossil_WtW = fuel_defaults_FEUM[fossil_name]["WtW"]
        bio_WtW = fuel_defaults_FEUM[bio_name]["WtW"]

        LHV_mix = fossil_LHV * fossil_ratio + bio_LHV * bio_ratio
        total_emission = fossil_WtW * fossil_LHV * fossil_ratio + bio_WtW * bio_LHV * bio_ratio
        WtW_mix = total_emission / LHV_mix

        return {"LHV": round(LHV_mix, 15), "WtW": round(WtW_mix, 15)}


    # 기본 연료 정의
    fuel_defaults = {}
    for fuel in FEUM_ttw_factors:
        LCV = FEUM_ttw_factors[fuel]["LCV"]
        LHV = round(LCV * 1_000_000, 15)
        WtW = calculate_wtw(fuel)
        fuel_defaults[fuel] = {"LHV": LHV, "WtW": WtW}

    # 혼합연료 추가
    fuel_defaults.update({
        "B24(HFO)": calculate_mixed_fuel("HFO (Grades RME to RMK)", "Bio(Fame)", 0.76, fuel_defaults),
        "B30(HFO)": calculate_mixed_fuel("HFO (Grades RME to RMK)", "Bio(Fame)", 0.7, fuel_defaults),
        "B24(LFO)": calculate_mixed_fuel("LFO (Grades RMA to RMD)", "Bio(Fame)", 0.76, fuel_defaults),
        "B30(LFO)": calculate_mixed_fuel("LFO (Grades RMA to RMD)", "Bio(Fame)", 0.7, fuel_defaults)
        })

    return fuel_defaults

# 연료 기본값 (GFI & FEUM 개별)
fuel_defaults_GFI = generate_GFI_fuel_defaults()
fuel_defaults_FEUM = generate_FEUM_fuel_defaults()

#GFI 계산기용 혼합연료 구분하기
def expand_mixed_fuel_GFI(fuel_data: list[dict], fuel_defaults_GFI: dict) -> list[dict]:
    expanded_rows = []
    for row in fuel_data:
        fuel_type = row["연료종류"]
        amt = row["사용량"]

        if fuel_type == "B24(VLSFO)":
            expanded_rows.append({
                "연료종류": "LFO (Grades RMA to RMD)",
                "LHV": fuel_defaults_GFI["LFO (Grades RMA to RMD)"]["LHV"],
                "WtW": fuel_defaults_GFI["LFO (Grades RMA to RMD)"]["WtW"],
                "사용량": amt * 0.76
            })
            expanded_rows.append({
                "연료종류": "Bio(Fame)",
                "LHV": fuel_defaults_GFI["Bio(Fame)"]["LHV"],
                "WtW": fuel_defaults_GFI["Bio(Fame)"]["WtW"],
                "사용량": amt * 0.24
            })
        elif fuel_type == "B24(HSFO)":
            expanded_rows.append({
                "연료종류": "HFO (Grades RME to RMK)",
                "LHV": fuel_defaults_GFI["HFO (Grades RME to RMK)"]["LHV"],
                "WtW": fuel_defaults_GFI["HFO (Grades RME to RMK)"]["WtW"],
                "사용량": amt * 0.76
            })
            expanded_rows.append({
                "연료종류": "Bio(Fame)",
                "LHV": fuel_defaults_GFI["Bio(Fame)"]["LHV"],
                "WtW": fuel_defaults_GFI["Bio(Fame)"]["WtW"],
                "사용량": amt * 0.24
            })
        elif fuel_type == "B30(VLSFO)":
            expanded_rows.append({
                "연료종류": "LFO (Grades RMA to RMD)",
                "LHV": fuel_defaults_GFI["LFO (Grades RMA to RMD)"]["LHV"],
                "WtW": fuel_defaults_GFI["LFO (Grades RMA to RMD)"]["WtW"],
                "사용량": amt * 0.7
            })
            expanded_rows.append({
                "연료종류": "Bio(Fame)",
                "LHV": fuel_defaults_GFI["Bio(Fame)"]["LHV"],
                "WtW": fuel_defaults_GFI["Bio(Fame)"]["WtW"],
                "사용량": amt * 0.3
            })
        elif fuel_type == "B30(HSFO)":
            expanded_rows.append({
                "연료종류": "HFO (Grades RME to RMK)",
                "LHV": fuel_defaults_GFI["HFO (Grades RME to RMK)"]["LHV"],
                "WtW": fuel_defaults_GFI["HFO (Grades RME to RMK)"]["WtW"],
                "사용량": amt * 0.7
            })
            expanded_rows.append({
                "연료종류": "Bio(Fame)",
                "LHV": fuel_defaults_GFI["Bio(Fame)"]["LHV"],
                "WtW": fuel_defaults_GFI["Bio(Fame)"]["WtW"],
                "사용량": amt * 0.3
            })
        else:
            expanded_rows.append(row)

    return expanded_rows

#GFI 입력 연료들 합치기 -> 중복 연료 합치기
def get_merged_gfi_data(fuel_data_list):
    grouped = defaultdict(lambda: {"사용량": 0.0, "LHV": 0.0, "WtW": 0.0})
    for row in fuel_data_list:
        key = (row["연료종류"], row["LHV"], row["WtW"])
        grouped[key]["사용량"] += row["사용량"]
        grouped[key]["LHV"] = row["LHV"]
        grouped[key]["WtW"] = row["WtW"]

    merged_list = []
    for (fuel_type, lhv, wtw), values in grouped.items():
        merged_list.append({
            "연료종류": fuel_type,
            "LHV": lhv,
            "WtW": wtw,
            "사용량": values["사용량"]
        })
    return merged_list

#FEUM 입력 연료들 합치기 -> 중복 연료 합치기
def get_merged_fueleu_data(fuel_data_list):
    grouped = defaultdict(lambda: {"역내": 0.0, "역외": 0.0, "LHV": 0.0, "WtW": 0.0})
    for row in fuel_data_list:
        key = (row["연료종류"], row["LHV"], row["WtW"])
        grouped[key]["역내"] += row["역내"]
        grouped[key]["역외"] += row["역외"]
        grouped[key]["LHV"] = row["LHV"]
        grouped[key]["WtW"] = row["WtW"]

    merged_list = []
    for (fuel_type, lhv, gfi), values in grouped.items():
        merged_list.append({
            "연료종류": fuel_type,
            "LHV": lhv,
            "WtW": gfi,
            "역내": values["역내"],
            "역외": values["역외"]
        })
    return merged_list

#FuelEU Martime 계산 함수 -> 입력된 연료 리스트에 혼합연료를 구분하고 시작함
def calculate_fueleu_result(fuel_data: list[dict],fuel_defaults_FEUM: dict) -> dict:
    # B24, B30 분리
    expanded_rows = []
    for row in fuel_data:
        fuel_type = row["연료종류"]
        inside = row["역내"]
        outside = row["역외"]

        if fuel_type == "B24(LFO)":
            expanded_rows += [
                {"연료종류": "LFO (Grades RMA to RMD)", "LHV": fuel_defaults_FEUM["LFO (Grades RMA to RMD)"]["LHV"],
                 "WtW": fuel_defaults_FEUM["LFO (Grades RMA to RMD)"]["WtW"], "역내": inside * 0.76, "역외": outside * 0.76},
                {"연료종류": "Bio(Fame)", "LHV": fuel_defaults_FEUM["Bio(Fame)"]["LHV"],
                 "WtW": fuel_defaults_FEUM["Bio(Fame)"]["WtW"], "역내": inside * 0.24, "역외": outside * 0.24}
            ]
        elif fuel_type == "B30(LFO)":
            expanded_rows += [
                {"연료종류": "LFO (Grades RMA to RMD)", "LHV": fuel_defaults_FEUM["LFO (Grades RMA to RMD)"]["LHV"],
                 "WtW": fuel_defaults_FEUM["LFO (Grades RMA to RMD)"]["WtW"], "역내": inside * 0.70, "역외": outside * 0.70},
                {"연료종류": "Bio(Fame)", "LHV": fuel_defaults_FEUM["Bio(Fame)"]["LHV"],
                 "WtW": fuel_defaults_FEUM["Bio(Fame)"]["WtW"], "역내": inside * 0.30, "역외": outside * 0.30}
            ]
        elif fuel_type == "B24(HFO)":
            expanded_rows += [
                {"연료종류": "HFO (Grades RME to RMK)", "LHV": fuel_defaults_FEUM["HFO (Grades RME to RMK)"]["LHV"],
                 "WtW": fuel_defaults_FEUM["HFO (Grades RME to RMK)"]["WtW"], "역내": inside * 0.76, "역외": outside * 0.76},
                {"연료종류": "Bio(Fame)", "LHV": fuel_defaults_FEUM["Bio(Fame)"]["LHV"],
                 "WtW": fuel_defaults_FEUM["Bio(Fame)"]["WtW"], "역내": inside * 0.24, "역외": outside * 0.24}
            ]
        elif fuel_type == "B30(HFO)":
            expanded_rows += [
                {"연료종류": "HFO (Grades RME to RMK)", "LHV": fuel_defaults_FEUM["HFO (Grades RME to RMK)"]["LHV"],
                 "WtW": fuel_defaults_FEUM["HFO (Grades RME to RMK)"]["WtW"], "역내": inside * 0.70, "역외": outside * 0.70},
                {"연료종류": "Bio(Fame)", "LHV": fuel_defaults_FEUM["Bio(Fame)"]["LHV"],
                 "WtW": fuel_defaults_FEUM["Bio(Fame)"]["WtW"], "역내": inside * 0.30, "역외": outside * 0.30}
            ]
        else:
            expanded_rows.append({
                "연료종류": fuel_type,
                "LHV": row["LHV"],
                "WtW": row["WtW"],
                "역내": inside,
                "역외": outside
            })        

    df_expanded = pd.DataFrame(expanded_rows)

    # 벌금 기준 발열량 계산
    df_expanded["역내_LHV"] = df_expanded["역내"] * df_expanded["LHV"]
    df_expanded["역외_LHV"] = df_expanded["역외"] * df_expanded["LHV"] * 0.5
    penalty_basis_energy = df_expanded["역내_LHV"].sum() + df_expanded["역외_LHV"].sum()

    # 계산 기준 발열량 계산
    def calc_adjusted_outside(row):
        fossil_fuels = ["HFO (Grades RME to RMK)", "LFO (Grades RMA to RMD)", "MDO", "MGO"]
        if row["연료종류"] not in fossil_fuels:
            return row["역외"] * row["LHV"]  # 100% 반영 (친환경 연료)
        else:
            return row["역외"] * row["LHV"] * 0.5  # 50% 반영 (화석연료)

    df_expanded["adj_outside_LHV"] = df_expanded.apply(calc_adjusted_outside, axis=1)
    df_expanded["total_adj_LHV"] = df_expanded["역내_LHV"] + df_expanded["adj_outside_LHV"]

    # GFI 낮은 순서대로 정렬
    df_sorted = df_expanded.sort_values(by="WtW").reset_index(drop=True)

    # 발열량 채워넣기
    cumulative_energy = 0
    selected_rows = []
    for _, row in df_sorted.iterrows():
        if cumulative_energy + row["total_adj_LHV"] <= penalty_basis_energy:
            used_energy = row["total_adj_LHV"]
        else:
            used_energy = penalty_basis_energy - cumulative_energy
            if used_energy <= 0:
                break
        cumulative_energy += used_energy
        selected_rows.append((row, used_energy))

    penalty_lhv_dict = {}
    penalty_emission_dict = {}

    for row, used_energy in selected_rows:
        fuel = row["연료종류"]
        gfi = row["WtW"]
        emission = used_energy * gfi / 1_000_000
        penalty_lhv_dict[fuel] = used_energy
        penalty_emission_dict[fuel] = emission

    # 결과 계산
    total_energy = 0
    total_emission = 0
    table = []
    for idx, (row, used_energy) in enumerate(selected_rows, start=1):
        ghg_intensity = row["WtW"]
        emission = used_energy * ghg_intensity / 1_000_000
        table.append({
            "No.": idx,
            "연료종류": row["연료종류"],
            "GHG Intensity (gCO₂eq/MJ)": round(ghg_intensity, 15),
            "반영 LCV (MJ)": round(used_energy, 15),
            "배출량 (tCO₂eq)": round(emission, 15)
        })
        total_energy += used_energy
        total_emission += emission

    avg_ghg_intensity = round(total_emission * 1_000_000 / total_energy, 15) if total_energy > 0 else 0
    standard_now = round(91.16 * 0.98, 15)
    cb = round((standard_now - avg_ghg_intensity) * total_energy / 1_000_000, 15)
    
    result = {
        "standard_now": standard_now,
        "total_energy": total_energy,
        "total_emission": total_emission
    }

    if avg_ghg_intensity > standard_now:
        penalty_eur = round((standard_now - avg_ghg_intensity) * total_energy * 2400 / 41000 / avg_ghg_intensity, 15)
    else:
        penalty_eur = 0

    df_result = pd.DataFrame(table)
    df_result.loc["합계"] = {
        "No.": "-",
        "연료종류": "Total",
        "GHG Intensity (gCO₂eq/MJ)": f"{avg_ghg_intensity:,.2f}",
        "반영 LCV (MJ)": f"{total_energy:,.2f}",
        "배출량 (tCO₂eq)": f"{total_emission:,.2f}"
    }

    return {
        "df_result": df_result,
        "avg_ghg_intensity": avg_ghg_intensity,
        "standard_now": standard_now,
        "cb": cb,
        "penalty_eur": penalty_eur,
        "total_energy": total_energy,
        "total_emission": total_emission,
        "df_expanded": df_expanded,
        "selected_rows": selected_rows,
        "penalty_lhv_dict": penalty_lhv_dict,        
    "penalty_emission_dict": penalty_emission_dict
    }

#Surplus 상태에서 화석연료 풀링 가능량 계산
def calculate_pooling_ton_by_fuel(result: dict, fuel_type: str, props: dict) -> float:
    standard = result["standard_now"]
    total_energy = result["total_energy"]
    total_emission = result["total_emission"]
    lhv = props["LHV"]
    gfi = props["WtW"]

    numerator = standard * total_energy - total_emission * 1_000_000
    denominator = lhv * (gfi - standard)

    if denominator == 0:
        return 0.0

    ton = numerator / denominator
    return max(round(ton, 15), 0.0)

# LNG, LPG, B100, B24, B30 역내 사용량 계산
def calculate_required_green_fuel_inside(result, fuel_type, fuel_defaults_FEUM):
    std = result["standard_now"]
    total_energy = result["total_energy"]
    total_emission = result["total_emission"] * 1_000_000  # tCO₂eq → gCO₂eq

    lhv = fuel_defaults_FEUM[fuel_type]["LHV"]
    gfi = fuel_defaults_FEUM[fuel_type]["WtW"]

    numerator = total_emission - std * total_energy
    denominator = lhv * (std - gfi)

    if numerator <= 0 or denominator <= 0:
        return 0.0

    required_mj = numerator / denominator
    return round(required_mj, 15)

# B24, B30 역외 사용량 계산
def calculate_b24_b30_outside_ton(result, fuel_type, fuel_defaults_FEUM):
    std = result["standard_now"]
    pb_energy = result["total_energy"]
    emission = result["total_emission"] * 1_000_000  # tCO₂eq → gCO₂eq

    if fuel_type not in fuel_defaults_FEUM:
        return 0.0

    lfo_lhv = fuel_defaults_FEUM["LFO (Grades RMA to RMD)"]["LHV"]
    lfo_gfi = fuel_defaults_FEUM["LFO (Grades RMA to RMD)"]["WtW"]
    hfo_lhv = fuel_defaults_FEUM["HFO (Grades RME to RMK)"]["LHV"]
    hfo_gfi = fuel_defaults_FEUM["HFO (Grades RME to RMK)"]["WtW"]
    b100_lhv = fuel_defaults_FEUM["Bio(Fame)"]["LHV"]
    b100_gfi = fuel_defaults_FEUM["Bio(Fame)"]["WtW"]

    if fuel_type == "B24(HFO)":
        bio_ratio = 0.24
        fossil_ratio = 0.76
        numerator = emission - std * pb_energy
        part1 = bio_ratio * b100_lhv * (std - b100_gfi)
        part2 = (fossil_ratio * 0.5 * hfo_lhv - bio_ratio * 0.5 * b100_lhv) * (hfo_gfi - std)
        denominator = part1 - part2

        if denominator <= 0 or numerator / denominator <= 0:
            return 0.0

    elif fuel_type == "B30(HFO)":
        bio_ratio = 0.30
        fossil_ratio = 0.70
        numerator = emission - std * pb_energy
        part1 = bio_ratio * b100_lhv * (std - b100_gfi)
        part2 = (fossil_ratio * 0.5 * hfo_lhv - bio_ratio * 0.5 * b100_lhv) * (hfo_gfi - std)
        denominator = part1 - part2

        if denominator <= 0 or numerator / denominator <= 0:
            return 0.0

    elif fuel_type == "B24(LFO)":
        bio_ratio = 0.24
        fossil_ratio = 0.76
        numerator = emission - std * pb_energy
        part1 = bio_ratio * b100_lhv * (std - b100_gfi)
        part2 = (fossil_ratio * 0.5 * lfo_lhv - bio_ratio * 0.5 * b100_lhv) * (lfo_gfi - std)
        denominator = part1 - part2

        if denominator <= 0 or numerator / denominator <= 0:
            return 0.0

    elif fuel_type == "B30(LFO)":
        bio_ratio = 0.30
        fossil_ratio = 0.70
        numerator = emission - std * pb_energy
        part1 = bio_ratio * b100_lhv * (std - b100_gfi)
        part2 = (fossil_ratio * 0.5 * lfo_lhv - bio_ratio * 0.5 * b100_lhv) * (lfo_gfi - std)
        denominator = part1 - part2

        if denominator <= 0 or numerator / denominator <= 0:
            return 0.0

    else:
        return 0.0

    return round(numerator / denominator, 4)

#B100 역외 사용량 첫번째 스텝
def step1_b100_required(row1, std, total_energy, total_emission, penalty, fuel_defaults_FEUM):
    # 연료 정보
    fuel = row1["연료종류"]
    lhv = row1["LHV"]
    gfi = row1["WtW"]
    inside = row1["역내"]
    outside = row1["역외"]

    b100_lhv = fuel_defaults_FEUM["Bio(Fame)"]["LHV"]
    b100_gfi = fuel_defaults_FEUM["Bio(Fame)"]["WtW"]

    # 1) 벌금 기준 에너지 (역내 100%, 역외 50%)
    fossil_energy = inside * lhv + outside * lhv * 0.5
    fossil_emission = fossil_energy * gfi

    # 2) 이론값
    if penalty > 0:
        theo_b100 = fossil_energy / b100_lhv * 2  # 역외 사용 50% 반영을 고려한 2배
    else:
        theo_b100 = 0

    # 3) 실질값 계산을 위한 현재 total 값 복사
    cumulative_energy = total_energy #벌금 기준 LCV 총합
    cumulative_emission = total_emission * 1_000_000  # tCO₂eq → gCO₂eq

    added_energy = theo_b100 * b100_lhv * 0.5
    added_emission = added_energy * b100_gfi

    new_energy = cumulative_energy - fossil_energy + added_energy
    new_emission = cumulative_emission - fossil_emission + added_emission
    new_avg = new_emission / new_energy if new_energy > 0 else float('inf')

    # 실질값 조건 만족 여부
    if new_avg < std and (inside + outside) > 0:
        numerator = std * cumulative_energy - cumulative_emission
        denominator = b100_lhv * (b100_gfi - 0.5 * gfi - std * 0.5)
        actual_b100 = numerator / denominator
    else:
        actual_b100 = 0

    # 최종값 = 작은 값
    final_b100 = min(theo_b100, actual_b100)
    return max(round(final_b100, 15), 0.0) if final_b100 > 0 else 0.0

#B100 역외 사용량 두번째 스텝
def step2_b100_required(row2, std, total_energy, total_emission, penalty, final_b100_step1, row1, fuel_defaults_FEUM):

    # 두 번째 연료 (예: HSFO)
    fuel2 = row2["연료종류"]
    lhv2 = row2["LHV"]
    gfi2 = row2["WtW"]
    inside2 = row2["역내"]
    outside2 = row2["역외"]

    # 첫 번째 연료 (예: VLSFO)
    lhv1 = row1["LHV"]
    gfi1 = row1["WtW"]

    # B100 정보
    b100_lhv = fuel_defaults_FEUM["Bio(Fame)"]["LHV"]
    b100_gfi = fuel_defaults_FEUM["Bio(Fame)"]["WtW"]

    # 이론값 계산
    fossil_energy2 = inside2 * lhv2 + outside2 * lhv2 * 0.5
    if penalty > 0:
        theo_b100_2 = fossil_energy2 / b100_lhv * 2
    else:
        theo_b100_2 = 0

    # 실질값 계산
    # 기존 누적 에너지/배출량
    cumulative_energy = total_energy
    cumulative_emission = total_emission * 1_000_000 \
        + final_b100_step1 * b100_lhv * b100_gfi \
    - final_b100_step1 * b100_lhv * 0.5 * gfi1

    # Step1 반영값
    added_energy1 = final_b100_step1 * b100_lhv * 0.5
    added_emission1 = added_energy1 * b100_gfi
    offset_emission1 = final_b100_step1 * b100_lhv * 0.5 * gfi1

    # Step2 이론값 반영값
    added_energy2 = theo_b100_2 * b100_lhv * 0.5
    added_emission2 = added_energy2 * b100_gfi
    offset_emission2 = fossil_energy2 * gfi2

    new_energy = cumulative_energy + added_energy1 + added_energy2
    new_emission = cumulative_emission - offset_emission1 - offset_emission2 + added_emission1 + added_emission2
    new_avg = new_emission / new_energy if new_energy > 0 else float('inf')

    if new_avg < std and (inside2 + outside2) > 0:
        numerator = std * (cumulative_energy + added_energy1) - (cumulative_emission + added_emission1 - offset_emission1)
        denominator = b100_lhv * (b100_gfi - 0.5 * gfi2 - std * 0.5)
        actual_b100 = numerator / denominator 
    else:
        actual_b100 = 0

    # 최종값: 이론값 vs 실질값 중 작은 값
    final_b100_2 = min(theo_b100_2, actual_b100)
    return max(round(final_b100_2, 15), 0.0) if final_b100_2 > 0 else 0.0

#B100 역외 사용량 세번째 스텝
def step3_b100_required(row3, std, total_energy, total_emission, penalty,
                         b100_result_step1, b100_result_step2,
                         row1, row2, fuel_defaults_FEUM):
    # LSMGO 연료 정보
    lhv3 = row3["LHV"]
    gfi3 = row3["WtW"]
    inside3 = row3["역내"]
    outside3 = row3["역외"]

    # 이전 연료 정보
    lhv1, gfi1 = row1["LHV"], row1["WtW"]
    lhv2, gfi2 = row2["LHV"], row2["WtW"]

    b100_lhv = fuel_defaults_FEUM["Bio(Fame)"]["LHV"]
    b100_gfi = fuel_defaults_FEUM["Bio(Fame)"]["WtW"]

    # LSMGO 벌금 기준 에너지 및 배출량
    fossil_energy3 = inside3 * lhv3 + outside3 * lhv3 * 0.5
    fossil_emission3 = fossil_energy3 * gfi3

    # 이론값 계산
    if penalty > 0:
        theo_b100 = fossil_energy3 / b100_lhv * 2
    else:
        theo_b100 = 0

    # 누적 에너지/배출량 계산 (이전 스텝 반영)
    cumulative_energy = total_energy \
        + 0.5 * b100_result_step1 * b100_lhv \
        + 0.5 * b100_result_step2 * b100_lhv

    cumulative_emission = total_emission * 1_000_000 \
        + b100_result_step1 * b100_lhv * b100_gfi \
        + b100_result_step2 * b100_lhv * b100_gfi \
        - b100_result_step1 * b100_lhv * 0.5 * gfi1 \
        - b100_result_step2 * b100_lhv * 0.5 * gfi2

    # 이론 B100 투입 시 변경 예상
    added_energy = theo_b100 * b100_lhv * 0.5
    added_emission = added_energy * b100_gfi
    removed_emission = fossil_emission3

    new_energy = cumulative_energy - fossil_energy3 + added_energy
    new_emission = cumulative_emission - removed_emission + added_emission
    new_avg = new_emission / new_energy if new_energy > 0 else float('inf')

    # 실질값 계산
    if new_avg < std and (inside3 + outside3) > 0:
        numerator = std * cumulative_energy - cumulative_emission
        denominator = b100_lhv * (b100_gfi - 0.5 * gfi3 - std * 0.5)
        actual_b100 = numerator / denominator
    else:
        actual_b100 = 0

    # 최종값 선택
    final_b100 = min(theo_b100, actual_b100)
    return max(round(final_b100, 15), 0.0) if final_b100 > 0 else 0.0

# B100 역외 총량 계산
def calculate_b100_total_required_stepwise(sorted_fuels, result, fuel_defaults_FEUM):
    std = result["standard_now"]
    total_energy = result["total_energy"]
    total_emission = result["total_emission"]
    penalty = result["penalty_eur"]

    b100_total = 0.0
    step1 = step2 = step3 = 0.0

    if len(sorted_fuels) >= 1:
        row1 = sorted_fuels[0]
        step1 = step1_b100_required(row1, std, total_energy, total_emission, penalty, fuel_defaults_FEUM)
        b100_total += step1

    if len(sorted_fuels) >= 2:
        row2 = sorted_fuels[1]
        step2 = step2_b100_required(row2, std, total_energy, total_emission, penalty,
                                    step1, sorted_fuels[0], fuel_defaults_FEUM)
        b100_total += step2

    if len(sorted_fuels) >= 3:
        row3 = sorted_fuels[2]
        step3 = step3_b100_required(row3, std, total_energy, total_emission, penalty,
                                    step1, step2, sorted_fuels[0], sorted_fuels[1], fuel_defaults_FEUM)
        b100_total += step3

    return round(b100_total, 15)

#GAS 역외 사용량 첫번째 스텝
def step1_gas_required(row1, std, total_energy, total_emission, penalty, fuel_defaults_FEUM, green_fuel_type):
    lhv = row1["LHV"]
    gfi = row1["WtW"]
    inside = row1["역내"]
    outside = row1["역외"]

    lng_lhv = fuel_defaults_FEUM[green_fuel_type]["LHV"]
    lng_gfi = fuel_defaults_FEUM[green_fuel_type]["WtW"]

    fossil_energy = inside * lhv + outside * lhv * 0.5
    fossil_emission = fossil_energy * gfi

    theo_lng = fossil_energy / lng_lhv * 2 if penalty > 0 else 0

    cumulative_energy = total_energy
    cumulative_emission = total_emission * 1_000_000

    added_energy = theo_lng * lng_lhv * 0.5
    added_emission = added_energy * lng_gfi

    new_energy = cumulative_energy - fossil_energy + added_energy
    new_emission = cumulative_emission - fossil_emission + added_emission
    new_avg = new_emission / new_energy if new_energy > 0 else float('inf')

    if new_avg < std and (inside + outside) > 0:
        numerator = std * cumulative_energy - cumulative_emission
        denominator = lng_lhv * (lng_gfi - 0.5 * gfi - std * 0.5)
        actual_lng = numerator / denominator
    else:
        actual_lng = 0

    final_lng = min(theo_lng, actual_lng)
    return max(round(final_lng, 15), 0.0) if final_lng > 0 else 0.0

#GAS 역외 사용량 두번째 스텝
def step2_gas_required(row2, std, total_energy, total_emission, penalty, final_lng_step1, row1, fuel_defaults_FEUM, green_fuel_type):
    fuel2 = row2["연료종류"]
    lhv2 = row2["LHV"]
    gfi2 = row2["WtW"]
    inside2 = row2["역내"]
    outside2 = row2["역외"]

    lhv1 = row1["LHV"]
    gfi1 = row1["WtW"]

    lng_lhv = fuel_defaults_FEUM[green_fuel_type]["LHV"]
    lng_gfi = fuel_defaults_FEUM[green_fuel_type]["WtW"]

    fossil_energy2 = inside2 * lhv2 + outside2 * lhv2 * 0.5
    theo_lng_2 = fossil_energy2 / lng_lhv * 2 if penalty > 0 else 0

    cumulative_energy = total_energy
    cumulative_emission = total_emission * 1_000_000 + final_lng_step1 * lng_lhv * lng_gfi - final_lng_step1 * lng_lhv * 0.5 * gfi1

    added_energy1 = final_lng_step1 * lng_lhv * 0.5
    added_emission1 = added_energy1 * lng_gfi
    offset_emission1 = final_lng_step1 * lng_lhv * 0.5 * gfi1

    added_energy2 = theo_lng_2 * lng_lhv * 0.5
    added_emission2 = added_energy2 * lng_gfi
    offset_emission2 = fossil_energy2 * gfi2

    new_energy = cumulative_energy + added_energy1 + added_energy2
    new_emission = cumulative_emission - offset_emission1 - offset_emission2 + added_emission1 + added_emission2
    new_avg = new_emission / new_energy if new_energy > 0 else float('inf')

    if new_avg < std and (inside2 + outside2) > 0:
        numerator = std * (cumulative_energy + added_energy1) - (cumulative_emission + added_emission1 - offset_emission1)
        denominator = lng_lhv * (lng_gfi - 0.5 * gfi2 - std * 0.5)
        actual_lng = numerator / denominator
    else:
        actual_lng = 0

    final_lng_2 = min(theo_lng_2, actual_lng)
    return max(round(final_lng_2, 15), 0.0) if final_lng_2 > 0 else 0.0

#GAS 역외 사용량 세번째 스텝
def step3_gas_required(row3, std, total_energy, total_emission, penalty,
                       lng_result_step1, lng_result_step2,
                       row1, row2, fuel_defaults_FEUM, green_fuel_type):
    lhv3 = row3["LHV"]
    gfi3 = row3["WtW"]
    inside3 = row3["역내"]
    outside3 = row3["역외"]

    lhv1, gfi1 = row1["LHV"], row1["WtW"]
    lhv2, gfi2 = row2["LHV"], row2["WtW"]

    lng_lhv = fuel_defaults_FEUM[green_fuel_type]["LHV"]
    lng_gfi = fuel_defaults_FEUM[green_fuel_type]["WtW"]

    fossil_energy3 = inside3 * lhv3 + outside3 * lhv3 * 0.5
    fossil_emission3 = fossil_energy3 * gfi3

    theo_lng = fossil_energy3 / lng_lhv * 2 if penalty > 0 else 0

    cumulative_energy = total_energy + 0.5 * lng_result_step1 * lng_lhv + 0.5 * lng_result_step2 * lng_lhv
    cumulative_emission = total_emission * 1_000_000 \
        + lng_result_step1 * lng_lhv * lng_gfi \
        + lng_result_step2 * lng_lhv * lng_gfi \
        - lng_result_step1 * lng_lhv * 0.5 * gfi1 \
        - lng_result_step2 * lng_lhv * 0.5 * gfi2

    added_energy = theo_lng * lng_lhv * 0.5
    added_emission = added_energy * lng_gfi
    removed_emission = fossil_emission3

    new_energy = cumulative_energy - fossil_energy3 + added_energy
    new_emission = cumulative_emission - removed_emission + added_emission
    new_avg = new_emission / new_energy if new_energy > 0 else float('inf')

    if new_avg < std and (inside3 + outside3) > 0:
        numerator = std * cumulative_energy - cumulative_emission
        denominator = lng_lhv * (lng_gfi - 0.5 * gfi3 - std * 0.5)
        actual_lng = numerator / denominator
    else:
        actual_lng = 0

    final_lng = min(theo_lng, actual_lng)
    return max(round(final_lng, 15), 0.0) if final_lng > 0 else 0.0

# GAS 역외 총량 계산
def calculate_lng_total_required_stepwise(sorted_fuels, result, fuel_defaults_FEUM, green_fuel_type):
    std = result["standard_now"]
    total_energy = result["total_energy"]
    total_emission = result["total_emission"]
    penalty = result["penalty_eur"]

    lng_total = 0.0
    step1 = step2 = step3 = 0.0

    if len(sorted_fuels) >= 1:
        row1 = sorted_fuels[0]
        step1 = step1_gas_required(row1, std, total_energy, total_emission, penalty, fuel_defaults_FEUM, green_fuel_type)
        lng_total += step1

    if len(sorted_fuels) >= 2:
        row2 = sorted_fuels[1]
        step2 = step2_gas_required(row2, std, total_energy, total_emission, penalty,
                                   step1, sorted_fuels[0], fuel_defaults_FEUM, green_fuel_type)  # ✅ 전달
        lng_total += step2

    if len(sorted_fuels) >= 3:
        row3 = sorted_fuels[2]
        step3 = step3_gas_required(row3, std, total_energy, total_emission, penalty,
                                   step1, step2, sorted_fuels[0], sorted_fuels[1], fuel_defaults_FEUM,green_fuel_type)  # ✅ 추가!
        lng_total += step3

    return round(lng_total, 15)

# 🌱 GFI 계산기(IMO 중기조치)
if menu == "GFI 계산기(IMO 중기조치)":
    st.title("🌱 GFI 계산기(IMO 중기조치)")

    if "fuel_data" not in st.session_state:
        st.session_state["fuel_data"] = []
    if "edit_index" not in st.session_state:
        st.session_state["edit_index"] = None
    if "manual_mode" not in st.session_state:
        st.session_state["manual_mode"] = False
    if "gfi_calculated" not in st.session_state:
        st.session_state["gfi_calculated"] = False

    # 연료 수정
    if st.session_state["edit_index"] is not None:
        st.subheader("✏️ 연료 수정")
        edit_row = st.session_state.fuel_data[st.session_state["edit_index"]]
        with st.form("edit_form"):
            fuel_type = st.selectbox("연료 종류", list(fuel_defaults_GFI.keys()),
                                     index=list(fuel_defaults_GFI.keys()).index(edit_row["연료종류"]))
            lhv = st.number_input("저위발열량 (MJ/Ton)", value=float(edit_row["LHV"]), min_value=0.0)
            wtw = st.number_input("Well-to-Wake 계수 (gCO₂eq/MJ)", value=float(edit_row["WtW"]), min_value=0.0)
            amount = st.number_input("사용량 (톤)", value=float(edit_row["사용량"]), min_value=0.0)
            submitted = st.form_submit_button("수정 완료")
            if submitted:
                st.session_state.fuel_data[st.session_state["edit_index"]] = {
                    "연료종류": fuel_type,
                    "LHV": lhv,
                    "WtW": wtw,
                    "사용량": amount
                }
                st.session_state["gfi_calculated"] = True
                st.session_state["edit_index"] = None
                st.rerun()

    # 연료 추가
    else:
        col1, col2 = st.columns([5, 2])
        with col1:
            st.subheader("➕ 연료 추가")
        with col2:
            button_label = "🔄 자동 입력" if st.session_state["manual_mode"] else "🔄 수동 입력"
            if st.button(button_label):
                st.session_state["manual_mode"] = not st.session_state["manual_mode"]
                st.rerun()
        with st.form("fuel_form"):
            fuel_type = st.selectbox("연료 종류", list(fuel_defaults_GFI.keys()))
            if st.session_state["manual_mode"]:
                lhv = st.number_input("저위발열량 (MJ/Ton)", min_value=0.0)
                wtw = st.number_input("Well-to-Wake 계수 (gCO₂eq/MJ)", min_value=0.0)
            else:
                lhv = fuel_defaults_GFI[fuel_type]["LHV"]
                wtw = fuel_defaults_GFI[fuel_type]["WtW"]
            amount = st.number_input("사용량 (톤)", min_value=0.0)
            submitted = st.form_submit_button("연료 추가")
            if submitted:
                st.session_state.fuel_data.append({
                    "연료종류": fuel_type,
                    "LHV": lhv,
                    "WtW": wtw,
                    "사용량": amount
                })
                st.session_state["gfi_calculated"] = False
                st.rerun()
    st.divider()
        
    # 입력한 연료 목록
    st.subheader("📋 입력한 연료 목록")
    
    # 헤더 행 추가
    header_cols = st.columns([0.5, 0.7, 1.6, 1.6, 1.6, 1.6, 0.7])
    with header_cols[0]:
        st.markdown("☑️")
    with header_cols[1]:
        st.markdown("**No.**")
    with header_cols[2]:
        st.markdown("**연료 종류**")
    with header_cols[3]:
        st.markdown("**LCV<br/>(MJ/Ton)**", unsafe_allow_html=True)
    with header_cols[4]:
        st.markdown("**GFI<br/>(gCO₂eq/MJ)**", unsafe_allow_html=True)
    with header_cols[5]:
        st.markdown("**사용량<br/>(Ton)**", unsafe_allow_html=True)
    with header_cols[6]:
        st.markdown("**수정**")
        
    # 본문 목록 출력 (GFI 계산기 용)
    delete_indices = []
    for i, row in enumerate(st.session_state.fuel_data, start=1):
        cols = st.columns([0.5, 0.7, 1.6, 1.6, 1.6, 1.6, 0.7])
        with cols[0]:
            selected = st.checkbox("", key=f"check_{i}")
        with cols[1]:
            st.markdown(f"<div style='padding-top: 9px'>{i}</div>", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"<div style='padding-top: 9px'>{row['연료종류']}</div>", unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"<div style='padding-top: 9px'><span style='color: green;'>{row['LHV']:,}</span></div>", unsafe_allow_html=True)
        with cols[4]:
            st.markdown(f"<div style='padding-top: 9px'><span style='color: green;'>{row['WtW']:,}</span></div>", unsafe_allow_html=True)
        with cols[5]:
            st.markdown(f"<div style='padding-top: 9px'><span style='color: green;'>{row['사용량']:,}</span></div>", unsafe_allow_html=True)
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

    col1, col2, col3, col4 = st.columns([1,4,4,1])
    # GFI 계산 버튼
    with col2:  
        if st.button("GFI 계산하기"):
            if st.session_state.fuel_data:
                st.session_state["gfi_calculated"] = True
            else:
                st.warning("연료를 먼저 입력해주세요.")

    with col3:
        if st.button("🧹 모든 연료 삭제"):
            st.session_state["fuel_data"] = []
            st.session_state["edit_index"] = None
            st.session_state["gfi_calculated"] = False
            st.rerun()
            
    # 계산 결과 표시
    if st.session_state["gfi_calculated"] and st.session_state.fuel_data:
        # ✨ 여기에 기존 GFI 계산기 로직 (그래프, 표 등) 붙이면 됨
        expanded_fuel_data = expand_mixed_fuel_GFI(st.session_state.fuel_data, fuel_defaults_GFI)
        df = pd.DataFrame(expanded_fuel_data)
        if not df.empty:
            df["총배출량(tCO2eq)"] = df["LHV"] * df["WtW"] * df["사용량"] * 1e-6
            df["총에너지(MJ)"] = df["LHV"] * df["사용량"]
            total_emission = df["총배출량(tCO2eq)"].sum()
            total_energy = df["총에너지(MJ)"].sum()
            gfi = total_emission * 1_000_000 / total_energy
            st.success(f"계산된 GFI: **{gfi:.2f} gCO₂eq/MJ**")
            
            # 기준값 설정 (2028년 기준 예시)
            base_now = 93.3 * (1 - 0.04)
            direct_now = 93.3 * (1 - 0.17)  # 17% 감축 기준

            # 연료별 GFI 계산을 위한 열 추가
            df["GHG Intensity (gCO₂eq/MJ)"] = df["WtW"]
            df["총 에너지 (MJ)"] = df["LHV"] * df["사용량"]
            df["총 배출량 (tCO₂eq)"] = df["LHV"] * df["WtW"] * df["사용량"] * 1e-6

            df_table = df[["연료종류", "GHG Intensity (gCO₂eq/MJ)", "총 에너지 (MJ)", "총 배출량 (tCO₂eq)"]].copy()
            df_table.insert(0, "No.", range(1, len(df_table) + 1))

            # 총합 행 추가
            df_total = pd.DataFrame([{
                "No.": "-",
                "연료종류": "Total",
                "GHG Intensity (gCO₂eq/MJ)": f"{gfi:.2f}",
                "총 에너지 (MJ)": df["총 에너지 (MJ)"].sum(),
                "총 배출량 (tCO₂eq)": df["총 배출량 (tCO₂eq)"].sum()
            }])
            df_table = pd.concat([df_table, df_total], ignore_index=True)

            # 쉼표 및 소수점 포맷 적용
            for col in ["총 에너지 (MJ)", "총 배출량 (tCO₂eq)"]:
                df_table[col] = df_table[col].apply(lambda x: f"{float(x):,.2f}")

            st.subheader("📄 GFI 계산 결과")
            st.dataframe(df_table, use_container_width=True, hide_index=True)
            

            # Tier 구분 및 CB, Penalty 계산
            if gfi >= base_now:
                tier = "Tier 2"
                cb2 = round(round(gfi - base_now, 4) * round(total_energy, 4) / 1e6, 4)
                cb1 = round(round(base_now - direct_now, 4) * round(total_energy, 4) / 1e6, 4)
                cb_total = cb1 + cb2
                penalty = round(cb1 * 100,0) + round(cb2 * 380, 0)
            elif gfi >= direct_now:
                tier = "Tier 1"
                cb1 = round(round(gfi - direct_now, 4) * round(total_energy, 4) / 1e6, 4)
                cb_total = cb1
                penalty = round(cb1 * 100, 0)
            else:
                tier = "Surplus"
                cb_total = round(round(gfi - direct_now, 4) * round(total_energy, 4)/ 1e6, 4)
                penalty = 0

            # 텍스트로 결과 요약
            st.markdown(f"**Tier 분류:** {tier}")
            st.markdown(f"**평균 GFI:** {gfi:,.2f} gCO₂eq/MJ")
            st.markdown(f"**총 배출량:** {total_emission:,.2f} tCO₂eq")
            st.markdown(f"**Compliance Balance (CB):** {cb_total:,.2f} tCO₂eq")

            if tier != "Surplus":
                st.markdown(f"**예상 벌금:** ${penalty:,.0f}")

            years = list(range(2028, 2036))
            base_gfi = [round(93.3 * r, 5) for r in [0.96, 0.94, 0.92, 0.876, 0.832, 0.788, 0.744, 0.7]]
            direct_gfi = [93.3*(1-0.17),93.3*(1-0.19),93.3*(1-0.21),93.3*(1-0.254),93.3*(1-0.298),93.3*(1-0.342),93.3*(1-0.386),93.3*(1-0.43)]

            # ZNZ 기준선 추가 (연도별 19.0 or 14.0)
            znz = [19.0 if year <= 2034 else 14.0 for year in years]

            # 그래프 시각화
            plt.figure(figsize=(8, 4))
            plt.plot(years, base_gfi, label="Base GFI(TIER2)", linestyle="--", marker="o")
            plt.plot(years, direct_gfi, label="Direct GFI(TIER1)", linestyle=":", marker="o")
            plt.hlines(gfi, 2028, 2035, color="red", linestyles="-", label=f"Your GFI: {gfi:.2f}")
            
            # ✅ ZNZ 선 추가
            plt.step(years, znz, where='post', label="ZNZ LINE", color="gold", linewidth=2)
            
            # ✅ 숫자 표기 (ZNZ)
            for x, y in zip(years, znz):
                offset = 0.1 if x == 2035 else 0.0  # 2035년만 오른쪽으로 살짝 이동
                plt.text(x + offset, y + 1, f"{y:.1f}", ha='center', va='bottom', fontsize=8, color="gold")

            # 나머지 텍스트
            for x, y in zip(years, base_gfi):
                plt.text(x, y + 1, f"{y:.1f}", ha='center', va='bottom', fontsize=8)
            for x, y in zip(years, direct_gfi):
                plt.text(x, y + 1, f"{y:.1f}", ha='center', va='bottom', fontsize=8)
            plt.xlabel("YEAR")
            plt.ylabel("gCO₂eq/MJ")
            plt.title("ACTUAL GFI vs TARGET GFI")
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
                    cb1 = round(round(bg - dg, 4) * round(total_energy, 4) / 1e6, 4)
                    cb2 = round(round(gfi - bg, 4) * round(total_energy, 4) / 1e6, 4)
                    p1 = round(cb1 * 100, 0)
                    p2 = round(cb2 * 380, 0)
                    total_penalty = p1 + p2
                    row["Tier 1 CB (tCO₂eq)"] = f"{cb1:,.2f} tCO₂eq"
                    row["Tier 2 CB (tCO₂eq)"] = f"{cb2:,.2f} tCO₂eq"
                    row["Tier 1 탄소세 ($)"] = f"${p1:,.0f}"
                    row["Tier 2 탄소세 ($)"] = f"${p2:,.0f}"

                elif gfi > dg:
                    row["Tier"] = "Tier 1"
                    cb1 = round(round(gfi - dg, 4) * round(total_energy, 4) / 1e6, 4)
                    p1 = round(cb1 * 100, 0)
                    total_penalty = p1
                    row["Tier 1 CB (tCO₂eq)"] = f"{cb1:,.0f} tCO₂eq"
                    row["Tier 1 탄소세 ($)"] = f"${p1:,.0f}"

                else:
                    row["Tier"] = "Surplus"
                    surplus = round(round(dg - gfi, 4) * round(total_energy, 4) / 1e6, 4)
                    row["Surplus (tCO₂eq)"] = f"{surplus:,.2f} tCO₂eq"
                    surplus_data.append({"연도": y, "Surplus (tCO₂eq)": f"{surplus:,.2f} tCO₂eq"})

                if row["Tier"] != "Surplus":
                    row["총 탄소세 ($)"] = f"${total_penalty:,.0f}"
                else:
                    row["총 탄소세 ($)"] = "None"

                data.append(row)

            # ✅ 열 순서 지정
            columns_order = ["연도", "Tier",
                 "Tier 1 CB (tCO₂eq)", "Tier 1 탄소세 ($)",
                 "Tier 2 CB (tCO₂eq)", "Tier 2 탄소세 ($)",
                 "Surplus (tCO₂eq)", "총 탄소세 ($)"]

            df_result = pd.DataFrame(data)
            df_result = df_result.reindex(columns=[col for col in columns_order if col in df_result.columns])

            st.subheader("📘 연도별 Compliance 결과")
            st.dataframe(df_result, use_container_width=True, hide_index=True)

            # 연도별 탄소세 시각화 준비
            df_penalty = df_result.copy()
            df_penalty["연도"] = df_penalty["연도"].astype(int)

            # 문자열 $ 제거 후 숫자로 변환
            for col in ["Tier 1 탄소세 ($)", "Tier 2 탄소세 ($)", "총 탄소세 ($)"]:
                if col in df_penalty.columns:
                    df_penalty[col] = df_penalty[col].replace("[$,]", "", regex=True).replace("None", "0").astype(float)

            # 그래프
            plt.figure(figsize=(10, 4))
            bar_width = 0.4
            x = np.arange(len(df_penalty))

            plt.bar(x - bar_width/2, df_penalty["Tier 1 탄소세 ($)"], width=bar_width, label="Tier 1 Carbon Tax", color="skyblue")
            if "Tier 2 탄소세 ($)" in df_penalty.columns:
                plt.bar(x + bar_width/2, df_penalty["Tier 2 탄소세 ($)"], width=bar_width, label="Tier 2 Carbon Tax", color="orange")

            plt.plot(x, df_penalty["총 탄소세 ($)"], label="Total Carbon Tax", color="red", marker="o", linewidth=2)
            
            #텍스트 표기
            for i, row in df_penalty.iterrows():
                offset = max(df_penalty["총 탄소세 ($)"]) * 0.07  # 7% 여유
                plt.text(x[i], row["총 탄소세 ($)"] + offset, f"${int(row['총 탄소세 ($)']):,}", ha='center', va='bottom', fontsize=8, color="red")
         
            # y축 최대값 조정
            max_val = df_penalty[["Tier 1 탄소세 ($)", "Tier 2 탄소세 ($)", "총 탄소세 ($)"]].max().max()
            plt.ylim(0, max_val * 1.2)

            plt.xticks(x, df_penalty["연도"])
            plt.xlabel("Year")
            plt.ylabel("Carbon Tax ($)")
            plt.title("Annual Carbon Tax")
            plt.legend()
            plt.grid(True, linestyle="--", alpha=0.3)

            st.pyplot(plt)

            if surplus_data:
                #st.subheader("🟢 Surplus 발생 연도")
                #st.dataframe(pd.DataFrame(surplus_data), use_container_width=True, hide_index=True)

                st.subheader("🔄 Surplus로 Tier2 탄소세 상쇄 가능한 각 유종별 연료량 (톤)")

                fuel_gfi_lhv = {
                    fuel: {
                    "GFI": fuel_defaults_GFI[fuel]["WtW"],
                    "LHV": fuel_defaults_GFI[fuel]["LHV"]
                    }
                     for fuel in fuel_defaults_GFI
                    }

                base_gfi_dict = dict(zip(years, base_gfi))
                
                offset_table = {"연도": []}
                for fuel in fuel_gfi_lhv.keys():
                    offset_table[fuel] = []

                for entry in surplus_data:
                    year = entry["연도"]
                    surplus_str = entry["Surplus (tCO₂eq)"]
                    surplus = float(surplus_str.replace(",", "").split()[0])
                    base = base_gfi_dict[year]

                    offset_table["연도"].append(year)

                    for fuel, info in fuel_gfi_lhv.items():
                        delta_gfi = info["GFI"] - base
                        if delta_gfi > 0:
                            energy_mj = surplus * 1_000_000 / delta_gfi
                            tonnage = energy_mj / info["LHV"]
                            offset_table[fuel].append(round(tonnage, 2))
                        else:
                            offset_table[fuel].append(0.0)
                            
                df_offset_wide = pd.DataFrame(offset_table)
                df_offset_formatted = df_offset_wide.copy()
                for col in df_offset_formatted.columns:
                    if col != "연도":
                        df_offset_formatted[col] = df_offset_formatted[col].apply(lambda x: f"{float(x):,.2f}")
                st.dataframe(df_offset_formatted, use_container_width=True, hide_index=True)
            direct_gfi_2028 = 93.3 * (1 - 0.17)
            base_gfi_2028 = 93.3 * (1 - 0.04)
            # ✅ Tier 2 상쇄용 친환경 연료 사용량 계산 (연도별)
            if gfi > direct_gfi_2028:  # GFI가 2028년 direct 보다 클 때만 계산

                st.subheader("🌿 탄소세 상쇄를 위한 각 유종별 연료량 (톤)")  
                green_fuels = {
                    fuel: {
                    "GFI": fuel_defaults_GFI[fuel]["WtW"],
                    "LHV": fuel_defaults_GFI[fuel]["LHV"]
                    }
                    for fuel in fuel_defaults_GFI
                        if fuel_defaults_GFI[fuel]["WtW"] < base_gfi_2028
                    }

                data_tier2 = {"연도": []}
                data_tier1 = {"연도": []}
                for fuel in green_fuels:
                    data_tier2[fuel] = []
                    data_tier1[fuel] = []

                for i, year in enumerate(years):
                    bg = base_gfi[i]
                    dg = direct_gfi[i]

                    # Tier 2 계산
                    if gfi > bg:
                        cb2 = (gfi - bg) * total_energy / 1e6  # Tier2 CB (tCO₂eq)
                        cb1 = (gfi - dg) * total_energy / 1e6   # Tier1 CB (tCO₂eq)

                        data_tier2["연도"].append(year)
                        data_tier1["연도"].append(year)

                        for fuel, info in green_fuels.items():
                            delta_gfi_t2 = bg - info["GFI"]
                            delta_gfi_t1 = dg - info["GFI"]

                            t2 = cb2 * 1_000_000 / delta_gfi_t2 / info["LHV"] if delta_gfi_t2 > 0 else 0
                            t1 = cb1 * 1_000_000 / delta_gfi_t1 / info["LHV"] if delta_gfi_t1 > 0 else 0

                            data_tier2[fuel].append(round(t2, 3))
                            data_tier1[fuel].append(round(t1, 3))

                    # Tier 1 계산만 발생한 경우도 포함
                    elif gfi > dg:
                        cb1 = (gfi - dg) * total_energy / 1e6   # Tier1 CB (tCO₂eq)
                        data_tier1["연도"].append(year)

                        for fuel, info in green_fuels.items():
                            delta_gfi_t1 = dg - info["GFI"]
                            t1 = cb1 * 1_000_000 / delta_gfi_t1 / info["LHV"] if delta_gfi_t1 > 0 else 0
                            data_tier1[fuel].append(round(t1, 3))


                df_t2 = pd.DataFrame(data_tier2)
                df_t1 = pd.DataFrame(data_tier1)
                
                # 👉 쉼표 포함 포맷팅
                df_t2_formatted = df_t2.copy()
                df_t1_formatted = df_t1.copy()
                for df in [df_t2_formatted, df_t1_formatted]:
                    for col in df.columns:
                        if col != "연도":
                            df[col] = df[col].apply(lambda x: f"{x:,.3f}")

                st.write("✅ Tier 2 탄소세 상쇄에 필요한 각 유종별 연료량 (톤)")
                st.dataframe(df_t2_formatted, use_container_width=True, hide_index=True)

                st.write("✅ Tier 1 탄소세 상쇄에 필요한 각 유종별 연료량 (톤)")
                st.dataframe(df_t1_formatted, use_container_width=True, hide_index=True)


        else:
            st.warning("먼저 연료를 입력해주세요.")
        
# 🚢 FuelEU Maritime 계산기
elif menu == "FuelEU Maritime":
    st.title("🚢 FuelEU Maritime 계산기")

    if "fueleu_data" not in st.session_state:
        st.session_state["fueleu_data"] = []
    if "fueleu_edit_index" not in st.session_state:
        st.session_state["fueleu_edit_index"] = None
    if "fueleu_manual_mode" not in st.session_state:
        st.session_state["fueleu_manual_mode"] = False
    if "fueleu_calculated" not in st.session_state:
        st.session_state["fueleu_calculated"] = False

    # 연료 입력 영역
    col1, col2 = st.columns([5, 2])
    with col1:
        st.subheader("➕ 연료 추가")
    with col2:
        button_label = "🔄 자동 입력" if st.session_state["fueleu_manual_mode"] else "🔄 수동 입력"
        if st.button(button_label):
            st.session_state["fueleu_manual_mode"] = not st.session_state["fueleu_manual_mode"]
            st.session_state["fueleu_calculated"] = False
            st.rerun()

    if st.session_state["fueleu_edit_index"] is not None:
        st.subheader("✏️ 연료 수정")
        row = st.session_state["fueleu_data"][st.session_state["fueleu_edit_index"]]
        with st.form("fueleu_edit_form"):
            fuel_type = st.selectbox("연료 종류", list(fuel_defaults_FEUM.keys()), index=list(fuel_defaults_FEUM.keys()).index(row["연료종류"]))
            lhv = st.number_input("저위발열량 (MJ/Ton)", value=float(row["LHV"]), min_value=0.0)
            gfi = st.number_input("GFI (gCO₂eq/MJ)", value=float(row["WtW"]), min_value=0.0)
            inside = st.number_input("역내 사용량 (톤)", value=float(row["역내"]), min_value=0.0)
            outside = st.number_input("역외 사용량 (톤)", value=float(row["역외"]), min_value=0.0)
            submitted = st.form_submit_button("수정 완료")
            if submitted:
                st.session_state["fueleu_data"][st.session_state["fueleu_edit_index"]] = {
                    "연료종류": fuel_type,
                    "LHV": lhv,
                    "WtW": gfi,
                    "역내": inside,
                    "역외": outside
                }
                st.session_state["fueleu_edit_index"] = None
                st.session_state["fueleu_calculated"] = True
                st.rerun()
    else:
        with st.form("fueleu_add_form"):
            fuel_type = st.selectbox("연료 종류", list(fuel_defaults_FEUM.keys()))
            if st.session_state["fueleu_manual_mode"]:
                lhv = st.number_input("저위발열량 (MJ/Ton)", min_value=0.0)
                gfi = st.number_input("GFI (gCO₂eq/MJ)", min_value=0.0)
            else:
                lhv = fuel_defaults_FEUM[fuel_type]["LHV"]
                gfi = fuel_defaults_FEUM[fuel_type]["WtW"]
            inside = st.number_input("역내 사용량 (톤)", min_value=0.0)
            outside = st.number_input("역외 사용량 (톤)", min_value=0.0)
            submitted = st.form_submit_button("연료 추가")
            if submitted:
                st.session_state["fueleu_data"].append({
                    "연료종류": fuel_type,
                    "LHV": lhv,
                    "WtW": gfi,
                    "역내": inside,
                    "역외": outside
                })
                st.session_state["fueleu_calculated"] = False
                st.rerun()

    # 입력 목록 테이블
    st.divider()
    st.subheader("📋 입력한 연료 목록")
    
    # 헤더 행 추가
    header_cols = st.columns([0.5, 1, 2, 2, 2, 2, 2, 1])
    with header_cols[0]:
        st.markdown("☑️")
    with header_cols[1]:
        st.markdown("**No.**")
    with header_cols[2]:
        st.markdown("**연료 종류**")
    with header_cols[3]:
        st.markdown("**LCV<br/>(MJ/Ton)**", unsafe_allow_html=True)
    with header_cols[4]:
        st.markdown("**GHG Intensity<br/>(gCO₂eq/MJ)**", unsafe_allow_html=True)
    with header_cols[5]:
        st.markdown("**역내 사용량<br/>(Ton)**", unsafe_allow_html=True)
    with header_cols[6]:
        st.markdown("**역외 사용량<br/>(Ton)**", unsafe_allow_html=True)
    with header_cols[7]:
        st.markdown("**수정**")
    
    # 본문 목록 출력
    delete_indices = []
    for i, row in enumerate(st.session_state["fueleu_data"], start=1):
        cols = st.columns([0.5, 1, 2, 2, 2, 2, 2, 1])
        with cols[0]:
            selected = st.checkbox("", key=f"feu_check_{i}")
        with cols[1]:
            st.markdown(f"<div style='padding-top: 9px'>{i}</div>", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"<div style='padding-top: 9px'>{row['연료종류']}</div>", unsafe_allow_html=True)
        with cols[3]:
            st.markdown(f"<div style='padding-top: 9px'><span style='color: green;'>{row['LHV']:,}</span></div>", unsafe_allow_html=True)
        with cols[4]:
            st.markdown(f"<div style='padding-top: 9px'><span style='color: green;'>{row['WtW']:,.5f}</span></div>", unsafe_allow_html=True)
        with cols[5]:
            st.markdown(f"<div style='padding-top: 9px'><span style='color: green;'>{row['역내']:,}</span></div>", unsafe_allow_html=True)
        with cols[6]:
            st.markdown(f"<div style='padding-top: 9px'><span style='color: green;'>{row['역외']:,}</span></div>", unsafe_allow_html=True)
        with cols[7]:
            if st.button("✏️", key=f"feu_edit_{i}"):
                st.session_state["fueleu_edit_index"] = i - 1
                st.rerun()
            if selected:
                delete_indices.append(i - 1)
    
    if delete_indices:
        if st.button("🗑️ 선택한 연료 삭제"):
            for index in sorted(delete_indices, reverse=True):
                st.session_state["fueleu_data"].pop(index)
            st.session_state["fueleu_edit_index"] = None
            st.session_state["fueleu_calculated"] = True
            st.rerun()
    col1, col2, col3, col4 = st.columns([1,4,4,1])
    
    with col2:        
        if st.button("FuelEU 계산하기"):
            if st.session_state["fueleu_data"]:
                st.session_state["fueleu_calculated"] = True
            else:
                st.warning("연료를 먼저 입력해주세요.")
    
    with col3:
        if st.button("🧹 모든 연료 삭제"):
            st.session_state["fueleu_data"] = []
            st.session_state["fueleu_edit_index"] = None
            st.session_state["fueleu_calculated"] = False
            st.rerun()

    if st.session_state["fueleu_calculated"] and st.session_state["fueleu_data"]:
        st.success("FuelEU 계산 완료")

        merged_fuel_data = get_merged_fueleu_data(st.session_state["fueleu_data"])
        result = calculate_fueleu_result(merged_fuel_data, fuel_defaults_FEUM)
    
    # ✅ HFO 풀링 가능량 미리 계산 (Δ1 + Δ2)
        vlsfo_props = {
                "LHV": fuel_defaults_FEUM["HFO (Grades RME to RMK)"]["LHV"],
                "WtW": fuel_defaults_FEUM["HFO (Grades RME to RMK)"]["WtW"]
                }       
        delta1_in = calculate_pooling_ton_by_fuel(result, "HFO", props=vlsfo_props)
        temp_data = st.session_state["fueleu_data"] + [{
    "연료종류": "HFO", "LHV": vlsfo_props["LHV"], "WtW": vlsfo_props["WtW"],
    "역내": delta1_in, "역외": 0.0
}]
        result2 = calculate_fueleu_result(temp_data, fuel_defaults_FEUM)
        delta2_in = calculate_pooling_ton_by_fuel(result2, "VLSFO", props=vlsfo_props)
        vlsfo_total_in = round(delta1_in + delta2_in, 4)

    # 결과 표 출력
        st.subheader("📄 FuelEU Maritime 계산 결과")
        df_result = result["df_result"]
        # 👉 쉼표 포함 포맷팅 적용
        for col in ["반영 LCV (MJ)", "배출량 (tCO₂eq)", "GHG Intensity (gCO2eq/MJ)"]:
            if col in df_result.columns:
                df_result[col] = df_result[col].apply(lambda x: f"{float(str(x).replace(',', '')):,.2f}")
        st.dataframe(df_result, use_container_width=True, hide_index=True)

        st.write(f"**평균 GHG Intensity:** {result['avg_ghg_intensity']:,.4f} gCO₂eq/MJ")
        st.write(f"**기준 GHG Intensity (2025):** {result['standard_now']:,.4f} gCO₂eq/MJ")
        st.write(f"**Compliance Balance (CB):** {result['cb']:,.2f} tCO₂eq")
        #st.markdown("### 🔍 B24/B30 연료 기본값")
        #for fuel in ["B24(HSFO)", "B30(HSFO)", "B24(VLSFO)", "B30(VLSFO)"]:
         #   if fuel in fuel_defaults_FEUM:
          #      lhv = fuel_defaults_FEUM[fuel]["LHV"]
           #     wtw = fuel_defaults_FEUM[fuel]["WtW"]
            #    st.write(f"{fuel}: LHV = {lhv} MJ/Ton, GHG Intensity = {wtw} gCO₂eq/MJ")
                
        #st.write(f"**예상 벌금:** € {result['penalty_eur']:,.3f}")
        # Surplus vs Deficit 분기
        if result["avg_ghg_intensity"] > result["standard_now"]:
            # Deficit → 벌금 표시
            st.write(f"**예상 탄소세:** € {result['penalty_eur']:,.0f}")
        else:
            st.write("**예상 탄소세:** 없음 (Surplus 상태)")

            if vlsfo_total_in is not None:
                pooling_revenue = round(62.2087697330022 * vlsfo_total_in, 0) #바꿔야해
                st.write(f"**VLSFO 풀링 가능량 (역내 기준):** {vlsfo_total_in:,.2f} 톤")
                st.write(f"**발생 Surplus 가치:** € {pooling_revenue:,.0f}")

    # 🌿 Surplus 상태 - 화석연료 풀링 가능량 계산 (Δ1 + Δ2)
        if result["avg_ghg_intensity"] < result["standard_now"]:
            st.info("📊 Surplus 상태입니다. Pooling 가능한 각 유종별 연료량을 계산합니다.")

            pooling_candidate_names = ["HFO (Grades RME to RMK)", "LFO (Grades RMA to RMD)", "MDO MGO (Grades DMX to DMB)"]
            pooling_candidates = {
                fuel: {
                    "LHV": fuel_defaults_FEUM[fuel]["LHV"],
                    "WtW": fuel_defaults_FEUM[fuel]["WtW"]
                    }
                    for fuel in pooling_candidate_names
                    }

            pooling_table = {"연료": [], "역내 톤수": [], "역외 톤수": []}

            for fuel, props in pooling_candidates.items():
                delta1_in = calculate_pooling_ton_by_fuel(result, fuel_type=fuel, props=props)
                temp_data = st.session_state["fueleu_data"] + [{
                "연료종류": fuel, "LHV": props["LHV"], "WtW": props["WtW"],
                "역내": delta1_in, "역외": 0.0
            }]
                result2 = calculate_fueleu_result(temp_data, fuel_defaults_FEUM)
                delta2_in = calculate_pooling_ton_by_fuel(result2, fuel_type=fuel, props=props)

                total_in = round(delta1_in + delta2_in, 4)
                total_out = round(total_in * 2, 4)

                pooling_table["연료"].append(fuel)
                pooling_table["역내 톤수"].append(total_in)
                pooling_table["역외 톤수"].append(total_out)

            st.subheader("🛢️ Pooling 가능한 각 유종별 연료량")
            df_pooling = pd.DataFrame(pooling_table)

            # 👉 쉼표 및 소수점 둘째자리 포맷 적용
            for col in ["역내 톤수", "역외 톤수"]:
                df_pooling[col] = df_pooling[col].apply(lambda x: f"{x:,.2f}")
            st.dataframe(df_pooling, use_container_width=True, hide_index=True)
            
            # 🔺 Deficit 상태 - 친환경 연료 필요량 
        elif result["avg_ghg_intensity"] > result["standard_now"]:
            st.info("📊 Deficit 상태입니다. 탄소세를 '0'로 만들기 위한 친환경 연료량을 계산합니다.")
            st.subheader("🌱 탄소세 상쇄를 위해 필요한 각 유종별 연료량")

            green_table = {
                "연료": [],
                "역내 톤수": [],
                "역외 톤수": []
            }

            # ✅ 연료 통합 및 정렬
            merged_fuel_data = get_merged_fueleu_data(st.session_state["fueleu_data"])
            sorted_fuels = sorted(merged_fuel_data, key=lambda x: -x["WtW"])

            # ✅ B100, LNG, LPG 역외 사용량 계산
            b100_out = calculate_b100_total_required_stepwise(sorted_fuels, result, fuel_defaults_FEUM)
            lng_out = calculate_lng_total_required_stepwise(
                sorted_fuels, result, fuel_defaults_FEUM, "LNG / LNG Diesel (dual fuel slow speed)"
            )
            lpg_pro_out = calculate_lng_total_required_stepwise(
                sorted_fuels, result, fuel_defaults_FEUM, "LPG - Propane"
            )
            lpg_but_out = calculate_lng_total_required_stepwise(
                sorted_fuels, result, fuel_defaults_FEUM, "LPG - Butane"
            )

            for fuel in [
                "LNG / LNG Diesel (dual fuel slow speed)",
                "B24(HFO)", "B24(LFO)",
                "B30(HFO)", "B30(LFO)",
                "Bio(Fame)",
                "LPG - Propane", "LPG - Butane"
            ]:
                in_ton = calculate_required_green_fuel_inside(result, fuel, fuel_defaults_FEUM)

                if fuel.startswith("B24") or fuel.startswith("B30"):
                    out_ton = calculate_b24_b30_outside_ton(result, fuel, fuel_defaults_FEUM)
                elif fuel == "Bio(Fame)":
                    out_ton = b100_out
                elif fuel == "LNG / LNG Diesel (dual fuel slow speed)":
                    out_ton = lng_out
                elif fuel == "LPG - Propane":
                    out_ton = lpg_pro_out
                elif fuel == "LPG - Butane":
                    out_ton = lpg_but_out
                else:
                    out_ton = 0.0

                green_table["연료"].append(fuel)
                green_table["역내 톤수"].append(in_ton)
                green_table["역외 톤수"].append(out_ton)

            # ✅ 쉼표 포맷 처리
            df_green = pd.DataFrame(green_table)
            for col in ["역내 톤수", "역외 톤수"]:
                df_green[col] = df_green[col].apply(lambda x: f"{x:,.3f}")
            st.dataframe(pd.DataFrame(df_green), use_container_width=True, hide_index=True)

                
                # 📈 GHG Intensity 기준선 vs 평균 GHG Intensity 그래프 및 연도별 CB/벌금 테이블
        if "avg_ghg_intensity" in result and "total_energy" in result:
            avg_ghg_intensity = result["avg_ghg_intensity"]
            total_energy = result["total_energy"]

            st.subheader("📈 GHG Intensity 기준선 vs 평균 GHG Intensity")

            steps = [
                (2025, 2029, round(91.16 * 0.98, 2)),
                (2030, 2034, round(91.16 * 0.94, 2)),
                (2035, 2039, round(91.16 * (1 - 0.145), 2)),
                (2040, 2044, round(91.16 * (1 - 0.31), 2)),
                (2045, 2049, round(91.16 * (1 - 0.62), 2)),
                (2050, 2052, round(91.16 * 0.2, 2)),
            ]
            years, standard_values = [], []
            for start, end, value in steps:
                for year in range(start, end + 1):
                    years.append(year)
                    standard_values.append(value)

            plt.figure(figsize=(10, 4))

            # 스텝 함수 (기준선)
            plt.step(years, standard_values, where='post', color="blue", linewidth=2, label="TARGET GHG Intensity")

            # 평균 GHG Intensity 빨간선
            plt.hlines(avg_ghg_intensity, 2025, 2050, colors="red", linestyles="--", linewidth=2, label=f"ACTUAL GHG Intensity: {avg_ghg_intensity:.2f} gCO₂eq/MJ")

            # 스텝 값 텍스트
            for start, end, value in steps:
                midpoint = (start + end) // 2
                plt.text(midpoint, value + 1, f"{value:.1f}", ha='center', va='bottom', fontsize=8, color="blue")

            plt.xlabel("YEAR")
            plt.ylabel("gCO₂eq/MJ")
            plt.xticks(range(2025, 2051, 5))
            plt.ylim(0, max(standard_values) + 10)
            plt.grid(True, linestyle="--", alpha=0.3)

            # ✅ GFI 그래프와 동일한 위치에 레전드 추가
            plt.legend(loc="center left", bbox_to_anchor=(0, 0.5))

            st.pyplot(plt)

        # 📘 GHG Intensity 기준선 vs 평균 GHG Intensity
        st.subheader("📘 연도 구간별 Compliance 결과")

        steps = [
            (2025, 2029, round(91.16 * 0.98, 4)),
            (2030, 2034, round(91.16 * 0.94, 4)),
            (2035, 2039, round(91.16 * (1 - 0.145), 4)),
            (2040, 2044, round(91.16 * (1 - 0.31), 4)),
            (2045, 2049, round(91.16 * (1 - 0.62), 4)),
            (2050, 2050, round(91.16 * 0.2, 4)),
        ]

        grouped_compliance = []

        for start, end, std_value in steps:
            delta = std_value - avg_ghg_intensity
            cb = delta * total_energy / 1_000_000  # tCO₂eq

            if delta < 0:
                tier = "Deficit"
                penalty = delta * total_energy * 2400 / 41000 / avg_ghg_intensity
            else:
                tier = "Surplus"
                penalty = 0

            grouped_compliance.append({
                "연도 구간": f"{start}–{end}",
                "기준 GHG Intensity": std_value,
                "Tier": tier,
                "CB (tCO₂eq)": round(cb, 3),
                "탄소세 (€)": f"€{penalty:,.0f}" if penalty else "-"
            })

        df_grouped = pd.DataFrame(grouped_compliance)
        # 쉼표 포맷 처리
        for col in ["CB (tCO₂eq)"]:
            df_grouped[col] = df_grouped[col].apply(lambda x: f"{x:,.2f}")

        st.dataframe(df_grouped, use_container_width=True, hide_index=True)

st.markdown(
    "<div style='text-align: left; font-size: 12px; color: gray; margin-top: 30px;'>"
    "© 2025 Hyundai Glovis E2E Integrated Strategy Team | jhkim36@glovis.net | 02-6393-9592<br>"
    "<i>※ 본 계산기는 현대글로비스 사내용으로 제작되었으며, 무단 복제·배포를 금합니다.</i>"
    "</div>",
    unsafe_allow_html=True
)
