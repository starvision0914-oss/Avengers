"""데이터 기반 차트 이미지 생성 (AI 이미지 생성 대신 — Gemini 이미지 모델은 무료 티어 할당량 0, 2026-07-19 확인).
matplotlib으로 실제 숫자 데이터를 시각화. dataviz 스킬 원칙 적용: 단일 시리즈는 단일 색상,
카테고리컬 다색 사용 금지(anti-pattern), 얇은 막대, 값 직접 라벨, 흐린 그리드."""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

KOREAN_FONT_PATH = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
if not os.path.exists(KOREAN_FONT_PATH):
    KOREAN_FONT_PATH = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

_font_prop = fm.FontProperties(fname=KOREAN_FONT_PATH) if os.path.exists(KOREAN_FONT_PATH) else None

# dataviz 스킬 palette.md 검증된 단일 계열(blue) — 라이트 서페이스 기준
COLOR_BAR = '#2a78d6'
COLOR_TEXT_PRIMARY = '#0b0b0b'
COLOR_TEXT_SECONDARY = '#52514e'
COLOR_GRID = '#e5e5e0'
COLOR_SURFACE = '#fcfcfb'
COLOR_REFERENCE_LINE = '#9a9990'


def generate_bar_chart(labels: list, values: list, title: str, output_path: str,
                        unit: str = '', reference_value: float = None, reference_label: str = '') -> str:
    """단일 시리즈 가로 막대 차트 PNG 생성. labels/values는 표시 순서 그대로(정렬 안 함 — 호출부에서 정렬).
    reference_value를 주면 평균 등 기준선을 점선으로 표시.
    반환: 저장된 파일 경로"""
    n = len(labels)
    fig_height = max(2.2, 0.62 * n + 1.0)
    fig, ax = plt.subplots(figsize=(7.5, fig_height), dpi=200)
    fig.patch.set_facecolor(COLOR_SURFACE)
    ax.set_facecolor(COLOR_SURFACE)

    y_pos = range(n)
    bars = ax.barh(y_pos, values, height=0.56, color=COLOR_BAR, zorder=3)

    if reference_value is not None:
        ax.axvline(reference_value, color=COLOR_REFERENCE_LINE, linestyle=(0, (4, 3)), linewidth=1.4, zorder=2)
        ax.text(reference_value, n - 0.3, f' {reference_label}', color=COLOR_TEXT_SECONDARY,
                fontsize=10, fontproperties=_font_prop, va='bottom', ha='left')

    max_val = max(values)
    decimals = 1 if any(abs(v - round(v)) > 0.001 for v in values) else 0
    for i, v in enumerate(values):
        ax.text(v + max_val * 0.015, i, f'{v:,.{decimals}f}{unit}', va='center', ha='left',
                fontsize=11, color=COLOR_TEXT_PRIMARY, fontproperties=_font_prop, zorder=4)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=11.5, color=COLOR_TEXT_PRIMARY, fontproperties=_font_prop)
    ax.invert_yaxis()

    ax.set_xlim(0, max_val * 1.22)
    ax.set_xticks([])
    for spine in ('top', 'right', 'bottom', 'left'):
        ax.spines[spine].set_visible(False)
    ax.grid(axis='x', color=COLOR_GRID, linewidth=0.8, zorder=1)
    ax.tick_params(axis='y', length=0)

    ax.set_title(title, fontsize=14, color=COLOR_TEXT_PRIMARY, fontproperties=_font_prop,
                 loc='left', pad=14, fontweight='bold')

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, facecolor=COLOR_SURFACE, bbox_inches='tight')
    plt.close(fig)
    return output_path
