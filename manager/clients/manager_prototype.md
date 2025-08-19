new accounts area:
1. Load all new hexogen and put guard on if there are any hexogen and add to db. button, shows progress
2. Add balance
3. Use items trader to trade items
4. view details (access db)
5. buy prime

Existing accounts area:
1. View all accounts status:
(waiting for free vm(takes precedence) (expected time to free, (basically earliest expected time)), waiting for balance (use items db to calculate expected time), farming (num stars, expected time to finish based on stars rpgoress: eg. 26/40 and use this time taken for 26 to predict time left))
Should be in a list or grid, sortable by status, clicking will give more details.

If a code is being run then it will show what's happening (different color) and when u click command line output will be shown.

2. view and edit details (access db)

3. View upcoming selling time, view items db visualized properly with charts

4. Manually sell (use items lister manually), gives warning if out of selling period or prices low

5. Armoury operations (link to the external application with that account selected) (external app opens)

6. create farmlabs farm job

7. cancel farmlabs farm job (after armoury pass farming is done for that account)

build scheduler (backend server process)


Scheduler:
1. During selling period all account with sellable items are sorted based on selling value and they are evenly spread out (high value accounts are spread out) and then the batches of 2 are made and then the items lister is run with accounts in batches of upto 2 (essentially an account that has only fever cases to sell can be paired with an account that has only stickers to sell but two of the same type cannot be in the same batch). Now this is done so that all items are sold at good prices. It is expected that when there are many accounts the items lister will run for many hours all the way up till around 11:30am and total time taken is noted and as more and more accounts become necessary it will also start earlier and earlier to ensure it does not go past 12 noon. (the time  taken for all accounts to be processed is also noted down).

2. Once items are sold on an account the armoruy pass is bought

3. a farmlabs bot job is created for that account

4. continuously monitor for armoruy pass completion and when its done cancel the corresponding farm job

5. redeem the items and run the items db updater

6. If there's enough balance to buy passes that is done, else wait for next selling period (step 1)

7. run the items trader to send these items to the fresh account (if this is the fresh account then this step is unnecessary).


panel area: (farmlabs)
1. Manual creation and modification of various types of jobs
2. viewing all jobs
3. for now it just links to farmlabs


third party marketplace:
1. a csfloat and a market.csgo section
2. It shows listable inventory
3. Allows u to select items en masse and list them (either for buy order price or at cheapest sell order price)
4. Allows you to view selling progress


Statistics:
1. Farm progress for the week and estimated time left
2. Farm statistics over time (number of passes, profit percentage over time, time spent farming, overall profitm etc.)
(Highly visual area)



* All graphs should be able to have adjustable x-axis and labels
* rename main dashboard to overview
* Ability to view logger logs is present for all parts

Overview:
currently farming bots number which can be clicked to take you to the accounts page with the currently farming bots selected
Orchestrator: Has currently running operations, schedule of future events
Docs link to the mkdocs webapp at bottom of the page    


New Accounts:
Main page has links to all other and has short doc on process
Load Hexogen: upload hexogen txt file and it does everything and puts final accs in db and shows progress
Add Balance: add balance, show progress, has options for choosing crpyto or inr (will also have a link to moogold to do it manually and auto update db)
Items Trader: Goes to the items trader page but with a restricted set of receiving accounts (non prime accounts that are activated)
Items Seller: Goes to the items seller page but with a restricted set of accounts (non prime accounts that have non zero items in items db)
Buy Prime: can select list of accounts and it buys prime on them and as many passes as possible (up to 5)


View Accounts:
Has accounts displayed with the most important details like:
steam_username, steam_avatar, status, Armoury, FUA status (%), password, generate_2fa_code_button, total_theoretical_value, region, vac_ban | items, bot_id, steam_balance | all other details
* Here the first group is always displayed, the 2nd group if expanded out and 3rd group only if explicitly selected as an option
* Can filter in each column by typing and select all
* Can also modify details or click to expand into full view (default view has reselected sizes for each row to look good)
* Here clicking items will list out the full list of items on the account in short
* An option to run a vac_ban check on all accounts will also be present


MarketPlace:

At the top have a disclaimer that these 2 are not implemented and links for:
https://market.csgo.com/ and https://csfloat.com/ in their corrospodning pages

Csfloat: Select an account and list all items for buy order price or for cheapest sell order price. it its cheapest sell order than progress bar will be over number of items. If its buy order price than it will not be over items but over various steps (received pruchase intention, sending trades, trades confirmed, money debited).

IT will also have a withdraw which won't be implemented for securetiy purposes. it will just take you to https://csfloat.com/profile/withdraw in a page for csfloat or it will take you to https://market.csgo.com/en/usercab/balance/withdrawing if its market.csgo

Have a logs popout that shows various logs here logs can loook like (these are just how the logs from my backend look like)

Also make sure that there is a csfloat/market.csgo balance displayed

Withdraw button that links you to: https://csfloat.com/profile/withdraw

