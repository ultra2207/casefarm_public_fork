import sys

import yaml


def load_config():
    config_path = r"C:\Users\Sivasai\Documents\GitHub\CaseFarm\config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


_config = load_config()
ROOT_DIR = _config["ROOT_DIR"]
sys.path.insert(0, ROOT_DIR)
from utils.logger import get_custom_logger

logger = get_custom_logger()


from ortools.linear_solver import pywraplp


def optimize_bin_covering(
    receiving_accounts: list[str],
    threshold: float,
    object_types: list[tuple[float, int, str, list]],
    initial_solution: dict,
) -> dict:
    # Number of accounts and object types
    N = len(receiving_accounts)
    M = len(object_types)

    # Create a dictionary to quickly look up object values
    object_value_dict = {name: value for value, _, name, _ in object_types}

    # Calculate the number of covered bins in the initial solution
    initial_covered_bins = sum(
        1
        for account in initial_solution.values()
        if sum(
            object_value_dict[obj.description.market_hash_name]
            for obj in account["objects"]
        )
        >= threshold
    )

    # Create the solver using Google OR-Tools
    solver = pywraplp.Solver.CreateSolver("SCIP")

    if not solver:
        logger.error("Could not create solver instance.")
        raise Exception("Could not create solver instance.")

    solver.SetTimeLimit(60000)
    logger.debug("Solver time limit set to 60000 milliseconds")

    # Decision variables
    A = {}
    for i in range(N):
        for j in range(M):
            A[i, j] = solver.IntVar(0, solver.infinity(), f"A_{i}_{j}")

    y = {}
    for i in range(N):
        y[i] = solver.BoolVar(f"y_{i}")

    # Objective function: minimize the total value of objects
    objective = solver.Objective()
    for i in range(N):
        for j in range(M):
            objective.SetCoefficient(A[i, j], object_types[j][0])
    objective.SetMinimization()

    # Constraints
    # 1. Bin covering constraint: y[i] is 1 if total value >= threshold
    for i in range(N):
        solver.Add(
            sum(A[i, j] * object_types[j][0] for j in range(M)) >= threshold * y[i]
        )

    # 2. Number of covered bins should match or exceed the number of covered bins in the initial solution
    solver.Add(sum(y[i] for i in range(N)) >= initial_covered_bins)

    # 3. Object quantity constraint
    for j in range(M):
        solver.Add(sum(A[i, j] for i in range(N)) <= object_types[j][1])

    # 4. Ensure that bins covered in the initial solution remain covered
    for i in range(N):
        account_name = receiving_accounts[i]
        if account_name in initial_solution:
            if (
                sum(
                    object_value_dict[obj.description.market_hash_name]
                    for obj in initial_solution[account_name]["objects"]
                )
                >= threshold
            ):
                solver.Add(y[i] == 1)
                logger.debug(f"Account {account_name} is required to remain covered")

    # Solve the problem with the time limit
    logger.info("Starting optimization process...")
    status = solver.Solve()
    logger.info(f"Optimization completed with status: {status}")

    # Post-optimization validation and result preparation
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        logger.success(
            f"Solver found a {'optimal' if status == pywraplp.Solver.OPTIMAL else 'feasible'} solution"
        )
        result = {}
        for i in range(N):
            assigned_objects = []
            total_value = 0
            for j in range(M):
                count = int(A[i, j].solution_value())
                if count > 0:
                    value, _, name, _ = object_types[j]
                    assigned_objects.extend([name] * count)
                    total_value += value * count

            if total_value >= threshold and len(assigned_objects) > 0:
                result[receiving_accounts[i]] = {
                    "objects": assigned_objects,
                    "total_value": total_value,
                }
            else:
                result[receiving_accounts[i]] = {"objects": [], "total_value": 0.0}
        return result
    else:
        logger.critical(
            f"Solver did not find an optimal solution within the time limit. Status: {status}"
        )
        raise Exception(
            f"Solver did not find an optimal solution within the time limit. Status: {status}"
        )


def bin_covering_greedy(
    receiving_accounts: list[str],
    threshold: float,
    object_types: list[tuple[float, int, str, list]],
) -> dict:
    object_pool = sorted(
        [
            [value, count, name, objects.copy()]
            for value, count, name, objects in object_types
        ],
        key=lambda x: x[0],
        reverse=True,
    )

    to_receive = receiving_accounts.copy()
    processed = {}

    logger.info("Starting greedy bin covering algorithm")

    while to_receive and any(obj[1] > 0 for obj in object_pool):
        account = to_receive[0]
        bin_content = []
        bin_value = 0

        # First, try to fill the bin with large items
        for i, (value, count, name, objects) in enumerate(object_pool):
            while count > 0 and bin_value + value <= threshold:
                bin_content.append(objects[0])
                bin_value += value
                count -= 1
                objects.pop(0)
                object_pool[i] = [value, count, name, objects]

            if bin_value >= threshold:
                break

        # If the bin is not full, try to fill it with smaller items
        if bin_value < threshold:
            logger.debug(
                f"Account {account} not filled with large items, trying smaller items"
            )
            for i, (value, count, name, objects) in enumerate(reversed(object_pool)):
                while count > 0 and bin_value < threshold:
                    bin_content.append(objects[0])
                    bin_value += value
                    count -= 1
                    objects.pop(0)
                    object_pool[-(i + 1)] = [value, count, name, objects]

                if bin_value >= threshold:
                    break

        if bin_value >= threshold:
            processed[account] = {"objects": bin_content, "total_value": bin_value}
            to_receive.pop(0)
            logger.info(f"Account {account} filled with value {bin_value}")
        else:
            logger.warning(f"Could not fill account {account} to threshold {threshold}")
            break  # If we can't fill an account, we stop

        # Remove empty object types from the pool
        object_pool = [obj for obj in object_pool if obj[1] > 0]

    logger.trace(
        f"Greedy algorithm completed. Processed {len(processed)} out of {len(receiving_accounts)} accounts"
    )
    return processed
