from typing import Any

from backend.core.emission_factors import get_factor
from ortools.linear_solver import pywraplp


class OptimizerService:
    @staticmethod
    def optimize_sourcing(
        suppliers: list[dict[str, Any]],
        total_demand_tonnes: float,
        min_esg_score: float = 0.0,
    ) -> dict[str, Any]:
        """Optimize material sourcing quantities from a list of suppliers to minimize carbon footprint

        using Google OR-Tools.

        Each supplier in `suppliers` has:
        - id: str
        - name: str
        - capacity_tonnes: float
        - production_emission_factor: float (tCO2e per tonne)
        - transport_distance_km: float
        - transport_mode: str (road, rail, air, sea)
        - esg_score: float (0 - 100)
        """
        # Create the linear solver with the GLOP backend.
        solver = pywraplp.Solver.CreateSolver("GLOP")
        if not solver:
            return {"success": False, "error": "Could not create OR-Tools solver"}

        infinity = solver.infinity()
        variables = {}
        
        # 1. Define decision variables: x[i] = tonnes to source from supplier i
        for idx, s in enumerate(suppliers):
            var_name = f"source_qty_{idx}"
            # x[i] >= 0 and x[i] <= supplier_capacity
            cap = s.get("capacity_tonnes", total_demand_tonnes)
            variables[idx] = solver.NumVar(0.0, float(cap), var_name)

        # 2. Add Constraints
        # Constraint A: Total sourced >= Total demand
        demand_constraint = solver.Constraint(total_demand_tonnes, infinity)
        for idx in variables:
            demand_constraint.SetCoefficient(variables[idx], 1.0)

        # Constraint B: Weighted ESG Score >= Min ESG Score
        # Sum(qty_i * esg_i) >= min_esg * Sum(qty_i) => Sum(qty_i * (esg_i - min_esg)) >= 0
        if min_esg_score > 0:
            esg_constraint = solver.Constraint(0.0, infinity)
            for idx, s in enumerate(suppliers):
                coeff = float(s.get("esg_score", 0.0) - min_esg_score)
                esg_constraint.SetCoefficient(variables[idx], coeff)

        # 3. Define Objective Function
        # Minimize sum of: qty * (production_factor + distance * transport_factor / 1000)
        objective = solver.Objective()
        for idx, s in enumerate(suppliers):
            prod_factor = float(s.get("production_emission_factor", 1.0))
            dist = float(s.get("transport_distance_km", 0.0))
            mode = s.get("transport_mode", "road")
            trans_factor = get_factor("transport", mode)
            
            # Total emission factor per tonne from this supplier
            total_factor = prod_factor + (dist * trans_factor / 1000.0)
            
            objective.SetCoefficient(variables[idx], total_factor)
        
        objective.SetMinimization()

        # 4. Solve the LP problem
        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            results = []
            total_emissions = 0.0
            total_sourced = 0.0
            weighted_esg_sum = 0.0

            for idx, s in enumerate(suppliers):
                qty = variables[idx].solution_value()
                if qty > 0.001:  # Filter out trivial numbers
                    prod_factor = float(s.get("production_emission_factor", 1.0))
                    dist = float(s.get("transport_distance_km", 0.0))
                    mode = s.get("transport_mode", "road")
                    trans_factor = get_factor("transport", mode)
                    
                    prod_emissions = qty * prod_factor
                    trans_emissions = qty * dist * trans_factor / 1000.0
                    supp_emissions = prod_emissions + trans_emissions
                    
                    results.append({
                        "supplier_id": s.get("id"),
                        "supplier_name": s.get("name"),
                        "sourced_quantity_tonnes": round(qty, 2),
                        "production_emissions_tco2e": round(prod_emissions, 2),
                        "transport_emissions_tco2e": round(trans_emissions, 2),
                        "total_emissions_tco2e": round(supp_emissions, 2),
                        "esg_score": s.get("esg_score"),
                    })
                    
                    total_emissions += supp_emissions
                    total_sourced += qty
                    weighted_esg_sum += qty * s.get("esg_score", 0.0)

            avg_esg = (weighted_esg_sum / total_sourced) if total_sourced > 0 else 0.0

            return {
                "success": True,
                "optimized_allocation": results,
                "total_emissions_tco2e": round(total_emissions, 2),
                "total_sourced_tonnes": round(total_sourced, 2),
                "average_esg_score": round(avg_esg, 2),
            }
        else:
            return {
                "success": False,
                "error": "The solver could not find a feasible solution satisfying all constraints.",
            }
            
    @staticmethod
    def calculate_alternative_routes(
        distance_km: float, weight_tonnes: float
    ) -> list[dict[str, Any]]:
        """Compare emissions of sending a shipment via different transport modes."""
        modes = ["road", "rail", "sea", "air"]
        comparisons = []

        for mode in modes:
            factor = get_factor("transport", mode)
            emissions = weight_tonnes * distance_km * factor / 1000.0
            comparisons.append({
                "mode": mode,
                "distance_km": distance_km,
                "weight_tonnes": weight_tonnes,
                "emission_factor_kg_per_tkm": factor,
                "total_emissions_tco2e": round(emissions, 4),
            })
            
        return sorted(comparisons, key=lambda x: x["total_emissions_tco2e"])
