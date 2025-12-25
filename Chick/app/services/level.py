# app/services/level.py
from app.models.user import User

# 定義每一段的「每升一級需要多少 EXP」
# (起始等級, 結束等級, 這一段每升 1 級需要的 EXP)
LEVEL_CONFIG = [
    (1, 10, 100),   # 1~10 級，每級 100 exp
    (11, 20, 200),  # 11~20 級，每級 200 exp
    (21, 30, 300),  # 21~30 級，每級 300 exp
    (31, 40, 500),  # 31~40 級，每級 500 exp
    (41, 50, 1000), # 41~50 級，每級 1000 exp
]

MAX_LEVEL = 50


def get_required_exp_for_level(level: int) -> int:
    """回傳『從目前等級升到下一級』所需要的 EXP。"""
    if level >= MAX_LEVEL:
        return 0
    for start, end, need in LEVEL_CONFIG:
        if start <= level <= end:
            return need
    # 理論上不會跑到這裡，保底用
    return LEVEL_CONFIG[-1][2]


def cumulative_exp_for_level(level: int) -> int:
    """回傳『到達某一等級』所需的『總累積 EXP』。
    - level = 1 代表起點，不需要 EXP，所以回傳 0。
    - level = 2 代表升到 2 級，需要 1 級的需求。
    """
    if level <= 1:
        return 0

    total = 0
    # 把 1 ~ (level-1) 的每級需求加總起來
    for lv in range(1, level):
        total += get_required_exp_for_level(lv)
    return total


def calc_level_from_exp(total_exp: int) -> int:
    """依照『總 EXP』算出等級。"""
    total_exp = max(0, total_exp or 0)
    level = 1

    while level < MAX_LEVEL:
        need = get_required_exp_for_level(level)
        if total_exp >= need:
            total_exp -= need
            level += 1
        else:
            break
    return level


def calc_exp_progress(total_exp: int) -> dict:
    """計算等級進度，用來做進度條或顯示『目前 / 需要』。

    回傳內容：
      - level: 目前等級
      - current_exp: 總 EXP（= user.exp）
      - exp_in_current_level: 這一級已經累積多少 EXP（分子）
      - required_for_next_level: 這一級需要多少 EXP 才能升級（分母）
      - remain_to_next_level: 還差多少 EXP（= 分母 - 分子，最小 0）
    """
    current_exp = max(0, total_exp or 0)
    level = calc_level_from_exp(current_exp)

    # 算目前這一級的起始累積 EXP
    level_start_exp = cumulative_exp_for_level(level)
    exp_in_current_level = current_exp - level_start_exp

    if level >= MAX_LEVEL:
        # 滿級：不再需要經驗
        required = 0
        remain = 0
    else:
        required = get_required_exp_for_level(level)
        remain = max(0, required - exp_in_current_level)

    return {
        "level": level,
        "current_exp": current_exp,
        "exp_in_current_level": exp_in_current_level,
        "required_for_next_level": required,
        "remain_to_next_level": remain,
    }


def apply_exp_and_update(user: User, delta_exp: int) -> None:
    """給 user 加上 delta_exp，並依照總 EXP 重算 level。"""
    new_total = max(0, (user.exp or 0) + delta_exp)
    user.exp = new_total
    user.level = calc_level_from_exp(new_total)
