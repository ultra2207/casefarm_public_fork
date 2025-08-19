import asyncio
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
import logging

import aiohttp

from utils.logger import get_custom_logger

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logger = get_custom_logger()
from database import get_db_price_usd_public, update_prices_from_market

PASS_CURRENCY_CAPITAL = "VND"
PASS_CURRENCY = PASS_CURRENCY_CAPITAL.lower()
PASS_VALUE = 400000

currencies_api = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{PASS_CURRENCY}.json"
stars = 40


async def reccomender() -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(currencies_api) as response:
            currencies_json = await response.json()
    star_usd_value = PASS_VALUE * currencies_json[PASS_CURRENCY]["usd"] / stars
    # Use asyncio and a semaphore to run get_db_price_usd_public calls concurrently, max 10 at a time
    semaphore = asyncio.Semaphore(10)

    async def get_price(name, currency="USD") -> float:
        async with semaphore:
            return await get_db_price_usd_public(name)

    # List of all item names to fetch prices for
    price_names = [
        "Sticker | High Heat",
        "Sticker | Rainbow Route (Holo)",
        "Sticker | Bolt Strike",
        "Sticker | Bolt Charge",
        "Sticker | Winding Scorch",
        "Sticker | Winding Scorch (Foil)",
        "Sticker | Scorch Loop",
        "Sticker | Hydro Wave",
        "Sticker | Hydro Stream",
        "Sticker | Scorch Loop (Reverse)",
        "Sticker | Hot Rod Heat",
        "Sticker | Boom Trail",
        "Sticker | Bolt Energy",
        "Sticker | Hydro Geyser",
        "Sticker | Boom Blast",
        "Sticker | Boom Epicenter",
        "Sticker | Boom Detonation",
        "Sticker | Boom Trail (Glitter)",
        "Sticker | Boom Detonation (Glitter)",
        "Sticker | Boom Blast (Glitter)",
        "Sticker | Boom Epicenter (Glitter)",
        "Sticker | Bolt Charge (Foil)",
        "Sticker | Bolt Strike (Foil)",
        "Sticker | Bolt Energy (Foil)",
        "Sticker | Ruby Stream (Lenticular)",
        "Sticker | Ruby Wave (Lenticular)",
        "Sticker | Googly Eye (Lenticular)",
        "Sticker | Side Eyes (Lenticular)",
        "Sticker | Red Shades (Foil)",
        "Sticker | Gold Teef (Foil)",
        "Sticker | Mustachio (Foil)",
        "Sticker | Taste Buddy (Holo)",
        "Sticker | Kawaii Eyes (Glitter)",
        "Sticker | Hypnoteyes (Holo)",
        "Sticker | Say Cheese (Holo)",
        "Sticker | From The Deep (Glitter)",
        "Sticker | Ribbon Tie",
        "Sticker | Flex",
        "Sticker | Blinky",
        "Sticker | Chompers",
        "Sticker | Taste Bud",
        "Sticker | Clown Nose",
        "Sticker | Quick Peek",
        "Sticker | Clown Wig",
        "Sticker | From The Deep",
        "Sticker | Fly High",
        "Sticker | Strike A Pose",
        "Sticker | Glare",
        "Sticker | XD",
        "Sticker | Lefty (T)",
        "Sticker | Lefty (CT)",
        "Gallery Case",
        "Fever Case",
    ]

    # Convert the list to the required dictionary format
    items_by_currency = {"USD": price_names}

    await update_prices_from_market(
        items_by_currency=items_by_currency, update_prices_in_usd=True
    )

    # Run all price fetches concurrently
    prices = await asyncio.gather(*(get_price(name) for name in price_names))

    # Unpack prices into variables as before
    (
        high_heat,
        rainbow,
        bolt_strike,
        bolt_charge,
        winding_scorch,
        winding_scorch_foil,
        scorch_loop,
        hydro_wave,
        hydro_stream,
        scorch_loop_reverse,
        hot_rod_heat,
        boom_trail,
        bolt_energy,
        hydro_geyser,
        boom_blast,
        boom_epicenter,
        boom_detonation,
        boom_trail_glitter,
        boom_detonation_glitter,
        boom_blast_glitter,
        boom_epicenter_glitter,
        bolt_charge_foil,
        bolt_strike_foil,
        bolt_energy_foil,
        ruby_stream,
        ruby_wave,
        googly_eye,
        side_eye,
        red_shades,
        gold_teef,
        mustachio,
        taste_buddy,
        kawaii_eye,
        hypnoteyes,
        say_cheese,
        from_the_deep,
        ribbon_tie,
        flex,
        blinky,
        chompers,
        taste_bud,
        clown_nose,
        quick_peek,
        clown_wig,
        deep,
        fly,
        pose,
        glare,
        xd,
        lefty,
        lefty_ct,
        gallery_case_value,
        fever_case_value,
    ) = prices

    elemental_craft_value = (
        high_heat / 18.72
        + bolt_strike / 18.72
        + bolt_charge / 18.72
        + winding_scorch / 18.72
        + scorch_loop / 18.72
        + hydro_wave / 18.72
        + hydro_stream / 18.72
        + scorch_loop_reverse / 18.72
        + hot_rod_heat / 18.72
        + boom_trail / 18.72
        + bolt_energy / 18.72
        + hydro_geyser / 18.72
        + boom_blast / 18.72
        + boom_epicenter / 18.72
        + boom_detonation / 18.72
        + boom_trail_glitter / 31.2
        + boom_detonation_glitter / 31.2
        + boom_blast_glitter / 31.2
        + boom_epicenter_glitter / 31.2
        + rainbow / 31.2
        + bolt_energy_foil / 124.8
        + bolt_charge_foil / 124.8
        + bolt_strike_foil / 124.8
        + winding_scorch_foil / 124.8
        + ruby_stream / 312
        + ruby_wave / 312
    )

    character_craft_value = (
        googly_eye / 312
        + side_eye / 312
        + red_shades / 93.6
        + gold_teef / 93.6
        + mustachio / 93.6
        + taste_buddy / 31.2
        + kawaii_eye / 31.2
        + hypnoteyes / 31.2
        + say_cheese / 31.2
        + from_the_deep / 31.2
        + ribbon_tie / 18.72
        + flex / 18.72
        + blinky / 18.72
        + chompers / 18.72
        + taste_bud / 18.72
        + clown_nose / 18.72
        + quick_peek / 18.72
        + clown_wig / 18.72
        + deep / 18.72
        + fly / 18.72
        + pose / 18.72
        + glare / 18.72
        + xd / 18.72
        + lefty / 18.72
        + lefty_ct / 18.72
    )

    # Sort the 5 values in descending order and log them
    values = [
        elemental_craft_value / (star_usd_value * 1.15),
        character_craft_value / (star_usd_value * 1.15),
        gallery_case_value / (star_usd_value * 2 * 1.15),
        fever_case_value / (star_usd_value * 2 * 1.15),
    ]
    print("\n\n\n")
    # Pair each item label with its value and sort by value descending
    item_labels = [
        "Elemental Craft Sticker Collection",
        "Character Craft Sticker Collection",
        "Gallery Case",
        "Fever Case",
    ]
    paired = list(zip(item_labels, values))
    sorted_items = sorted(paired, key=lambda iv: iv[1], reverse=True)

    logger.info("Most profitable items sorted by expected value:")
    for name, val in sorted_items:
        logger.info(f"{name}: {val:.4f}")

    print("\n\n\n")

    # Custom recommendation logic
    def get_case_max():
        gc_val = dict(paired)["Gallery Case"]
        fc_val = dict(paired)["Fever Case"]
        if gc_val >= fc_val:
            return "Gallery Case", gc_val
        else:
            return "Fever Case", fc_val

    def recommend(sorted_items):
        best_name, best_val = sorted_items[0]
        case_name, case_val = get_case_max()
        if best_name in ("Fever Case", "Gallery Case"):
            return best_name
        elif best_name == "Elemental Craft Sticker Collection":
            if best_val >= 1.05 * case_val:
                return best_name
            else:
                return case_name
        else:
            return best_name

    recommendation = recommend(sorted_items)
    logger.success(f"Recommended item to redeem: {recommendation}")

    return recommendation


if __name__ == "__main__":
    asyncio.run(reccomender())
