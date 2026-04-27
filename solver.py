"""
PROWESS — Physical-Remote-Optimized Work Environment Scheduling Software
Core CP-SAT solver module.
"""

from __future__ import annotations
import math
from typing import Any
from ortools.sat.python import cp_model


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
N_DAYS = len(DAYS)
SCALE = 1000  # multiply float weights → integers for CP-SAT

# Default solver tuning knobs (all overridable via data['solver_params'])
DEFAULTS = {
    "max_time_seconds":     30.0,
    "num_workers":          4,
    "pairwise_bonus_factor":  0.3,   # pair-in-office bonus, relative to p_grp
    "carpool_bonus_factor":   0.4,   # carpool same-status bonus, relative to p_nic
    "overlap_penalty_factor": 2.0,   # penalty multiplier for missing weekly overlap target
    "subgroup_bonus_factor":  0.5,   # subgroup all-in bonus, relative to group overlap_weight
}


def _iscale(x: float) -> int:
    return int(round(x * SCALE))


def solve(data: dict) -> dict:
    """
    data keys
    ---------
    org:
        max_seats: int
        min_daily_in_person: int
        priority_employees: float  (0–1, sum to 1)
        priority_groups: float
        priority_niceties: float
        weeks: int

    employees: list of dicts
        id, name, geo_cluster, vacation_days,
        min_office_days_per_week, max_office_days_per_week, preferred_days

    groups: list of dicts
        id, name, members, min_overlap_days_per_week, subgroups, overlap_weight

    solver_params: dict (all optional, fall back to DEFAULTS)
        max_time_seconds, num_workers,
        pairwise_bonus_factor, carpool_bonus_factor,
        overlap_penalty_factor, subgroup_bonus_factor
    """
    org       = data["org"]
    employees = data["employees"]
    groups    = data.get("groups", [])
    n_weeks   = org.get("weeks", 1)
    n_total_days = N_DAYS * n_weeks

    max_seats  = org["max_seats"]
    min_daily  = org.get("min_daily_in_person", 0)
    p_emp = org.get("priority_employees", 0.33)
    p_grp = org.get("priority_groups",    0.50)
    p_nic = org.get("priority_niceties",  0.17)

    # ── Tuning knobs ────────────────────────────────────────────────────────
    sp = data.get("solver_params", {})
    max_time_seconds  = float(sp.get("max_time_seconds",     DEFAULTS["max_time_seconds"]))
    num_workers       = int(  sp.get("num_workers",          DEFAULTS["num_workers"]))
    pairwise_factor   = float(sp.get("pairwise_bonus_factor",  DEFAULTS["pairwise_bonus_factor"]))
    carpool_factor    = float(sp.get("carpool_bonus_factor",   DEFAULTS["carpool_bonus_factor"]))
    overlap_penalty   = float(sp.get("overlap_penalty_factor", DEFAULTS["overlap_penalty_factor"]))
    subgroup_factor   = float(sp.get("subgroup_bonus_factor",  DEFAULTS["subgroup_bonus_factor"]))

    emp_ids  = [e["id"] for e in employees]
    n_emp    = len(employees)

    model = cp_model.CpModel()

    # ── Decision variables ───────────────────────────────────────────────────
    in_office: list[list[cp_model.BoolVarT]] = []
    for i, e in enumerate(employees):
        row = []
        for d in range(n_total_days):
            row.append(model.new_bool_var(f"office_{e['id']}_d{d}"))
        in_office.append(row)

    # ── Hard constraints ─────────────────────────────────────────────────────
    # 1. Vacation: force out
    for i, e in enumerate(employees):
        for d in e.get("vacation_days", []):
            if d < n_total_days:
                model.add(in_office[i][d] == 0)

    # 2. Seat capacity per day
    for d in range(n_total_days):
        model.add(sum(in_office[i][d] for i in range(n_emp)) <= max_seats)

    # 3. Min daily occupancy
    for d in range(n_total_days):
        available = sum(
            1 for i, e in enumerate(employees)
            if d not in e.get("vacation_days", [])
        )
        effective_min = min(min_daily, available)
        if effective_min > 0:
            model.add(sum(in_office[i][d] for i in range(n_emp)) >= effective_min)

    # 4. Per-employee weekly min/max
    for i, e in enumerate(employees):
        mn = e.get("min_office_days_per_week", 0)
        mx = e.get("max_office_days_per_week", N_DAYS)
        for w in range(n_weeks):
            week_days = range(w * N_DAYS, (w + 1) * N_DAYS)
            non_vac   = [d for d in week_days if d not in e.get("vacation_days", [])]
            if non_vac:
                week_sum = sum(in_office[i][d] for d in non_vac)
                model.add(week_sum >= mn)
                model.add(week_sum <= min(mx, len(non_vac)))

    # ── Objective terms (integer-scaled) ────────────────────────────────────
    objective_terms = []

    # ── A. Employee preference matching ──────────────────────────────────────
    if p_emp > 0:
        emp_weight = _iscale(p_emp)
        for i, e in enumerate(employees):
            preferred = set(e.get("preferred_days", []))
            for w in range(n_weeks):
                for wd in range(N_DAYS):
                    d = w * N_DAYS + wd
                    if d in e.get("vacation_days", []):
                        continue
                    if wd in preferred:
                        # preferred remote → reward being OUT of office
                        objective_terms.append(emp_weight * (1 - in_office[i][d]))
                    else:
                        objective_terms.append(emp_weight * in_office[i][d])

    # ── B. Group overlap ─────────────────────────────────────────────────────
    group_overlap_vars: dict[str, list] = {}

    if p_grp > 0:
        for grp in groups:
            gid        = grp["id"]
            members    = grp.get("members", [])
            m_indices  = [emp_ids.index(mid) for mid in members if mid in emp_ids]
            if len(m_indices) < 2:
                continue

            grp_w          = _iscale(p_grp * grp.get("overlap_weight", 1.0))
            min_overlap_req = grp.get("min_overlap_days_per_week", 1)

            all_in_days = []
            for d in range(n_total_days):
                all_in     = model.new_bool_var(f"allin_{gid}_d{d}")
                m_vars     = [in_office[mi][d] for mi in m_indices]
                model.add_bool_and(m_vars).only_enforce_if(all_in)
                model.add_bool_or([v.negated() for v in m_vars]).only_enforce_if(all_in.negated())
                all_in_days.append(all_in)
                objective_terms.append(grp_w * len(m_indices) * all_in)

                # Pairwise bonus (partial overlap counts too)
                for a in range(len(m_indices)):
                    for b in range(a + 1, len(m_indices)):
                        pair = model.new_bool_var(f"pair_{gid}_{m_indices[a]}_{m_indices[b]}_d{d}")
                        model.add_bool_and(
                            [in_office[m_indices[a]][d], in_office[m_indices[b]][d]]
                        ).only_enforce_if(pair)
                        model.add_bool_or([
                            in_office[m_indices[a]][d].negated(),
                            in_office[m_indices[b]][d].negated(),
                        ]).only_enforce_if(pair.negated())
                        objective_terms.append(_iscale(p_grp * pairwise_factor) * pair)

            group_overlap_vars[gid] = all_in_days

            # Weekly overlap target (soft penalty for falling short)
            for w in range(n_weeks):
                week_all_in  = [all_in_days[w * N_DAYS + wd] for wd in range(N_DAYS)]
                overlap_count = sum(week_all_in)
                slack         = model.new_int_var(0, N_DAYS, f"overlap_slack_{gid}_w{w}")
                model.add(slack == min_overlap_req - overlap_count)
                clamped       = model.new_int_var(0, N_DAYS, f"clamped_slack_{gid}_w{w}")
                model.add_max_equality(clamped, [slack, model.new_constant(0)])
                objective_terms.append(
                    -_iscale(p_grp * grp.get("overlap_weight", 1.0) * overlap_penalty) * clamped
                )

            # Subgroup bonuses
            for sg in grp.get("subgroups", []):
                sg_indices = [emp_ids.index(mid) for mid in sg if mid in emp_ids]
                if len(sg_indices) < 2:
                    continue
                sg_w = _iscale(p_grp * grp.get("overlap_weight", 1.0) * subgroup_factor)
                for d in range(n_total_days):
                    sg_all_in = model.new_bool_var(
                        f"sg_allin_{gid}_{'_'.join(map(str, sg_indices))}_d{d}"
                    )
                    sg_vars = [in_office[si][d] for si in sg_indices]
                    model.add_bool_and(sg_vars).only_enforce_if(sg_all_in)
                    model.add_bool_or([v.negated() for v in sg_vars]).only_enforce_if(sg_all_in.negated())
                    objective_terms.append(sg_w * sg_all_in)

    # ── C. Niceties ──────────────────────────────────────────────────────────
    cluster_map: dict[str, list[int]] = {}
    for i, e in enumerate(employees):
        cluster_map.setdefault(e.get("geo_cluster", "default"), []).append(i)

    if p_nic > 0:
        nic_w = _iscale(p_nic)

        # Mon/Fri equity: maximise the minimum Mon-or-Fri days worked
        mf_indices = [d for d in range(n_total_days) if d % N_DAYS in (0, 4)]
        if mf_indices and n_emp > 1:
            mf_counts = []
            for i in range(n_emp):
                cnt = model.new_int_var(0, len(mf_indices), f"monfri_{i}")
                model.add(cnt == sum(
                    in_office[i][d] for d in mf_indices
                    if d not in employees[i].get("vacation_days", [])
                ))
                mf_counts.append(cnt)
            min_mf = model.new_int_var(0, len(mf_indices), "min_monfri")
            model.add_min_equality(min_mf, mf_counts)
            objective_terms.append(nic_w * min_mf)

        # Carpool: employees in the same geo cluster should share office days
        for cl, idxs in cluster_map.items():
            if len(idxs) < 2:
                continue
            for d in range(n_total_days):
                for a in range(len(idxs)):
                    for b in range(a + 1, len(idxs)):
                        same     = model.new_bool_var(f"carpool_{cl}_{idxs[a]}_{idxs[b]}_d{d}")
                        both_in  = model.new_bool_var(f"ci_{cl}_{idxs[a]}_{idxs[b]}_d{d}")
                        both_out = model.new_bool_var(f"co_{cl}_{idxs[a]}_{idxs[b]}_d{d}")
                        model.add_bool_and(
                            [in_office[idxs[a]][d], in_office[idxs[b]][d]]
                        ).only_enforce_if(both_in)
                        model.add_bool_or([
                            in_office[idxs[a]][d].negated(), in_office[idxs[b]][d].negated()
                        ]).only_enforce_if(both_in.negated())
                        model.add_bool_and([
                            in_office[idxs[a]][d].negated(), in_office[idxs[b]][d].negated()
                        ]).only_enforce_if(both_out)
                        model.add_bool_or([
                            in_office[idxs[a]][d], in_office[idxs[b]][d]
                        ]).only_enforce_if(both_out.negated())
                        model.add_bool_or([both_in, both_out]).only_enforce_if(same)
                        model.add_bool_and(
                            [both_in.negated(), both_out.negated()]
                        ).only_enforce_if(same.negated())
                        objective_terms.append(_iscale(p_nic * carpool_factor) * same)

    # ── Maximise ─────────────────────────────────────────────────────────────
    model.maximize(sum(objective_terms))

    # ── Solve ─────────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    solver.parameters.num_search_workers  = num_workers
    solver.parameters.log_search_progress = False

    status = solver.solve(model)

    result: dict[str, Any] = {
        "status":   solver.status_name(status),
        "feasible": status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
        "objective": solver.objective_value if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
        "schedules":             {},
        "group_overlap_summary": {},
        "carpool_summary":       {},
        "daily_counts":          [],
        "weeks": n_weeks,
        "solver_params_used": {
            "max_time_seconds":     max_time_seconds,
            "num_workers":          num_workers,
            "pairwise_bonus_factor":  pairwise_factor,
            "carpool_bonus_factor":   carpool_factor,
            "overlap_penalty_factor": overlap_penalty,
            "subgroup_bonus_factor":  subgroup_factor,
        },
    }

    if not result["feasible"]:
        return result

    # ── Extract solved values ────────────────────────────────────────────────
    solved_office = [
        [solver.value(in_office[i][d]) for d in range(n_total_days)]
        for i in range(n_emp)
    ]

    # ── Compute detailed scores ──────────────────────────────────────────────
    scores: dict[str, Any] = {
        "employee": {},
        "group":    {},
        "nicety":   {"mon_fri_equity": 0, "carpool": 0, "raw": 0, "score": 0.0},
        "total_raw": 0,
        "total":     0.0,
    }

    # A. Employee preference score
    if p_emp > 0:
        emp_weight_raw = _iscale(p_emp)
        for i, e in enumerate(employees):
            pref_score_raw = 0
            preferred = set(e.get("preferred_days", []))
            for w in range(n_weeks):
                for wd in range(N_DAYS):
                    d = w * N_DAYS + wd
                    if d in e.get("vacation_days", []):
                        continue
                    val = solved_office[i][d]
                    if wd in preferred:
                        pref_score_raw += emp_weight_raw * (1 - val)
                    else:
                        pref_score_raw += emp_weight_raw * val
            scores["employee"][e["id"]] = {
                "raw":   pref_score_raw,
                "score": pref_score_raw / SCALE,
            }
            scores["total_raw"] += pref_score_raw

    # B. Group overlap score
    if p_grp > 0:
        for grp in groups:
            gid       = grp["id"]
            members   = grp.get("members", [])
            m_indices = [emp_ids.index(mid) for mid in members if mid in emp_ids]
            if len(m_indices) < 2:
                continue

            grp_w_raw       = _iscale(p_grp * grp.get("overlap_weight", 1.0))
            min_overlap_req  = grp.get("min_overlap_days_per_week", 1)
            grp_score_raw    = 0

            full_overlap_days = []
            for d in range(n_total_days):
                all_in = all(solved_office[mi][d] for mi in m_indices)
                if all_in:
                    grp_score_raw += grp_w_raw * len(m_indices)
                    full_overlap_days.append(d)
                for a in range(len(m_indices)):
                    for b in range(a + 1, len(m_indices)):
                        if solved_office[m_indices[a]][d] and solved_office[m_indices[b]][d]:
                            grp_score_raw += _iscale(p_grp * pairwise_factor)

            for w in range(n_weeks):
                week_all_in  = [all(solved_office[mi][w * N_DAYS + wd] for mi in m_indices) for wd in range(N_DAYS)]
                overlap_count = sum(week_all_in)
                slack         = max(0, min_overlap_req - overlap_count)
                grp_score_raw -= _iscale(p_grp * grp.get("overlap_weight", 1.0) * overlap_penalty) * slack

            for sg in grp.get("subgroups", []):
                sg_indices = [emp_ids.index(mid) for mid in sg if mid in emp_ids]
                if len(sg_indices) < 2:
                    continue
                sg_w_raw = _iscale(p_grp * grp.get("overlap_weight", 1.0) * subgroup_factor)
                for d in range(n_total_days):
                    if all(solved_office[si][d] for si in sg_indices):
                        grp_score_raw += sg_w_raw

            scores["group"][gid] = {
                "name":  grp["name"],
                "raw":   grp_score_raw,
                "score": grp_score_raw / SCALE,
                "full_overlap_days": full_overlap_days,
            }
            scores["total_raw"] += grp_score_raw

    # C. Niceties score
    if p_nic > 0:
        nic_w_raw     = _iscale(p_nic)
        nic_score_raw = 0
        mf_equity_raw = 0
        carpool_raw   = 0

        mf_indices = [d for d in range(n_total_days) if d % N_DAYS in (0, 4)]
        if mf_indices and n_emp > 1:
            mf_counts = [
                sum(solved_office[i][d] for d in mf_indices if d not in employees[i].get("vacation_days", []))
                for i in range(n_emp)
            ]
            min_mf      = min(mf_counts) if mf_counts else 0
            mf_equity_raw = nic_w_raw * min_mf
            nic_score_raw += mf_equity_raw

        for cl, idxs in cluster_map.items():
            if len(idxs) < 2:
                continue
            for d in range(n_total_days):
                for a in range(len(idxs)):
                    for b in range(a + 1, len(idxs)):
                        if solved_office[idxs[a]][d] == solved_office[idxs[b]][d]:
                            v = _iscale(p_nic * carpool_factor)
                            carpool_raw   += v
                            nic_score_raw += v

        scores["nicety"]["mon_fri_equity"] = mf_equity_raw / SCALE
        scores["nicety"]["carpool"]        = carpool_raw / SCALE
        scores["nicety"]["raw"]            = nic_score_raw
        scores["nicety"]["score"]          = nic_score_raw / SCALE
        scores["total_raw"] += nic_score_raw

    scores["total"] = scores["total_raw"] / SCALE

    # ── Per-employee schedules ───────────────────────────────────────────────
    for i, e in enumerate(employees):
        schedule = []
        for d in range(n_total_days):
            if d in e.get("vacation_days", []):
                schedule.append("vacation")
            elif solved_office[i][d]:
                schedule.append("office")
            else:
                schedule.append("home")
        result["schedules"][e["id"]] = {
            "name": e["name"],
            "schedule": schedule,
            "office_days_total": sum(1 for s in schedule if s == "office"),
        }

    # ── Daily occupancy ──────────────────────────────────────────────────────
    for d in range(n_total_days):
        result["daily_counts"].append(sum(solved_office[i][d] for i in range(n_emp)))

    # ── Group overlap summary ────────────────────────────────────────────────
    for grp in groups:
        gid = grp["id"]
        if gid not in group_overlap_vars:
            continue
        overlap_days = [d for d, var in enumerate(group_overlap_vars[gid]) if solver.value(var)]
        result["group_overlap_summary"][gid] = {
            "name":               grp["name"],
            "members":            grp["members"],
            "full_overlap_days":  overlap_days,
            "full_overlap_count": len(overlap_days),
            "target_per_week":    grp.get("min_overlap_days_per_week", 1),
        }

    # ── Carpool summary ──────────────────────────────────────────────────────
    for cl, idxs in cluster_map.items():
        if len(idxs) < 2:
            result["carpool_summary"][cl] = {
                "members":      [employees[i]["id"]   for i in idxs],
                "member_names": [employees[i]["name"] for i in idxs],
                "solo": True,
            }
            continue

        pair_alignment: dict[str, int] = {}
        total_aligned  = 0
        n_pairs        = len(idxs) * (len(idxs) - 1) // 2
        total_possible = n_total_days * n_pairs

        for d in range(n_total_days):
            for a in range(len(idxs)):
                for b in range(a + 1, len(idxs)):
                    ia, ib = idxs[a], idxs[b]
                    if solved_office[ia][d] == solved_office[ib][d]:
                        key = f"{employees[ia]['name']} & {employees[ib]['name']}"
                        pair_alignment[key] = pair_alignment.get(key, 0) + 1
                        total_aligned += 1

        result["carpool_summary"][cl] = {
            "members":       [employees[i]["id"]   for i in idxs],
            "member_names":  [employees[i]["name"] for i in idxs],
            "solo":          False,
            "pair_alignment": pair_alignment,
            "avg_alignment":  total_aligned / max(1, n_pairs),
            "pct_aligned":    total_aligned / max(1, total_possible),
            "n_days":         n_total_days,
        }

    result["scores"] = scores
    return result
