1. runs stage_0 at 7pm.
2. runs stage_1 at the time in json (of the top 3 sort earliest to latest and if earliest is best then choose that, if not but earliest is like less than 1.5% difference from the best overall than pick earliest, like that work your way).

remaining:
3. Armoury pass farm jobs are created for the accounts in the TickTick farm list.
4. When pass farming is complete for the accounts, user is asked to redeem items for that account using standard arb panel (manual_request_with_notofication for pass redeeming). Then pua updater is run that selects the next pua account if current pua reaches fua.


Daily once:
pass_price updation using steamassets.com
if pass_price is updated does an emergency is_armoury=0 then notifies me and starts account region
movement process and waits for my input. (full region movement involves creating the corresponding number of new accounts in new region, sending them trades from existing accounts to buy prime and armoury passes on them and setting them to is_armoury after trades are sent) This full region movement has not been automated yet.

pua_threshold updation by getting prices dynamically. 

Make it with streamlit.

pass_prices, updated business sim, updated pua threshold, inventory value calculator, vac check on all accounts (defaults to false and not run), if pass prices update then trigger region switching sim with new data, update reccomender, revenue growth simulation direct. Make these files take the pass information from config.yaml 
(all these added to end of stage 1)

implement this:

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