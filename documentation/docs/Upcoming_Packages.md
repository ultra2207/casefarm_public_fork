Acc generation:

1. Use Hexogen to autogen accounts using alex fogur long lived hotmail/outlook emails or buy verified steam accounts from hexogen store. Buy the generator when Frost finally geta a private hcaptcha solver implemented into it.

Prime Activation:

1. When all accounts are fully upgraded and you need to make new prime account(s) (Note: In the long run if you are making multiple fully upgraded accounts at once, the corresponding amount needed for steamgiftcards will be sent to main account to sell on third party) predict the future price and transfer the corresponding amount of items to main account and then wait 10 days. 

After doing this send out the items to the accounts in an account by account process where you go to the next account once the current account has enough items to be fully upgraded.

Price prediction using: (estimated selling price of the cases on third party are 10 days out price which is considered safe. Selling price of cases on steam are calculated as a very safe maximum average selling price based on expected range to exist from 7 days to 10 days out (usually just 1.2-1.3x of the needed price is transferred (if u need to transfer 100, you transfer 125))). (Note: this step is optional if existing cash reserves are enough to cover the giftcard expenses)

2. After 10 days, list the third party allocated cases on third party using api.

3. Sell the third party items and withdraw the balance. (automation later)

4. Buy balance on moogold and redeem giftcards. (done in a batched process, refer to Giftcard redeemer) (automate later)

5. Use the giftcards, account by account getting each to $5.
   Here, youve already waited for 10 days so the inventory items are already marketable.

6. Sell the items and buy prime and up to 5 passes (as many as possible) while doing this, update the database tags.

Usage: 

Now that you have switched fully to crypto by selling drops to crypto and withdrawing the crypto and buying giftcards with crypto, only notifications will be sent and no intervention is necessary.

Armoury Pass Activation:

1. The FUA accounts are constantly running their item listers and botlooter trader, sending excees items to the new account.

2. When a new account receives an item, its marketability time is noted in the new items table in the database.
When an item becomes marketable, the items lister is automatically run on the PUA, selling all items.

3. If there is enough wallet balance to buy an armoury pass, the armoury pass buyer is used to buy the pass and the database is updated.


Data Science Process:

1. third party marketplaces data gatherer subprocess

2. Steam scraper subprocess

3. Data science module to do things
    1. Do price prediction for steam and third party (refer to step 2 for details)

    2. Allocate what needs to be sold on third party and the cases allocated to each steam account (put in a list) (modify the case trader to use this list, use the existing optimizer to make this)
    
    3. Calculate the best time of the day to sell and the expected price, also calculating best time of the next 7 days and their predicted optimal selling prices for step 9 of the prime adding process. (usually in the morning)

third party:

1. Multiple third party marketplaces will be integreted into the api. The front end face of the api will be unifeid with one lister, acceptor, etc. with the option to set the marketplace specifically or put it on auto upon which it would simply pick the best one to list that specific item on considering all facotrs (pirce on thatvarious marketplaces , liquidity of the item on various marketplaces, all selling and withdrawawl fees).

2. A Process that keeps waiting for sales to occur and upon receiving a trade request uses the third party api to check its legitimacy and then it confirms the trade request. (forever running server process) (Trade acceptor process)

3. code to list items for sale on third party. it gets the list of items to sell as args or from temp file which is passed as an argument and then lists those competitively (either lowest price or matching price if only a few exist at that price (use fractions to determine this)). advanced feature is checking every few minutes to ensure that prices are competitive and if not lowers them.
(continuously running third party listing package)

4. A utility that tells the current value of all items if sold on third party (util)


Keep track of the instant skins selling bot on telegram where u sell for 65% of steam price. Will not be used at preseant but something to be aware off.


Farm:

1. farmlabs v2 config updater and launcher both in visual package. buttons with stdout display farmlabs launcher package rund updater script before hand ehich checks if anything has changed then updation if not continue to launch
(unifined farmlabs launcher package and a util script integrated into the package)
 
for large scale farming: Gui has a statistics visual with features like progress of current week (armoury stars using armoury stars checker) and previous week including details like passes farmed number and percentage including previous weeks and avg time taken for completion on previous weeks and list if items obtained. If using multiple pcs for farming, send all info to the main server and run the gui there which shows split out visuals for each pc and its allotted accounts and an overall visual for the entire farm.

Main farm server thread runs on the server and sends commands to the sub farm threads running on each farming pc and receives back data ysed to update the gui (and sends commands to restart or redeem armoury stars or buy new passes). Every week it updates its pool of accounts using the latest database. the sub farmlabs threads then launch farmlabs and run till they're finished (all consecutive armoury passes exhausted) upon which it is closed. Whenever that account has armoury pass ready again it restarts the vm and resumes farming. At all times main thread receives back info to update its gui. The consiecutive armoruy pass configs are sent to the farm subthreads and those are updated as soon as the main database is updated whenever an account is upgraded. THe farm subthreads use these consecutive passes expecteation to manage the vm and will shut down the vm once the next pass is not anytime soon to save resources.

Farm gui built using react.

cycle start to end management:

1. At the end of every match the armoury stars progress is automatically checked by the farm subthread using Armoury_pass_progress_checker. if its full then all live windows and steam is immediately killed. Then the armoury stars redeemer is run and then the buyer is run (by this point the previous weeks cases woudlve been sold and you have enough to rebuy the armoury pass). Then once all 5 armoruy passes are there the farmlabs is restarted by running the updater. Whenever the account has run out of consecutive armoruy farms to run, the machine is then shutdown automatically by the subthread and will be relaunched when the next armoeuy pass becomes available. This will make it easier for the other vms to run faster and also conserve electricity.

2. whenever a botjob needing input is created pit in 1 and 2. In the long run make it work based off of the items price, use aiosteampy for this.

4. Whenever a new bot account gets prime. If upgrade cycle finishes with it being only prime with no armoury passes (no more immediate pending upgrades). The bot task will be for the next level, 1xp with the condition to stop task upon drop detection.  it is then queued up. When it eventually gets an armoeuy pass it is put into the same bucket as the existing armoury pass accounts.
If the account is new and also has an armoury pass it is given a similarly high xp level threshold and put into the same bucket as all the existing armoruy accounts.

5. Whenever any bot has its armoury pass upgraded/acquired an armoury farm bot task is made. It is then queued up to run.

6. Drops are not automatically traded. Instead trades are initiated in 2 scenarios:
    1. if a claim job occurs that specific item is instantly sent to main using custom written code
    2. Whenever an account has tradable items that item is traded immediately with botlooter (item trades are grouped for 15 mins and proxies are used).

7. Armoury pass completion ststus and prime drop completion status are tracked (this will be used for the stats page)

Here the farm subthreads are threads running on the farming pcs (farmlabs launcher threads) that launch and oversee the farming process. They run outside the vm and have their own subthreads inside the vm. This way they can also shutdown and relaunch vms.

(Server-unified farmlabs package with gui running externally on main server which has data sent to it)
Note: Local pcs receive commands over the ethernet and Shadow.tech pcs receive commands over the internet

Farm subthreads:
Each farm subthread is in charge of farming a specific account till their consecutive armoury passes are completed. They're also responsible for doing armoruy pass redemptions, purchases, monitoring armoruy pass completion and shutting down and starting up the vms. These have sub threads of their own running on the vms.

Note: The account receiving all of the cases will not send its cases out and instantly list all of them on the steam community market. This fact also makes real life farming slightly faster than the sims, at least in the beginning which still lasts for a while.


Armoury redemption profitablity calculator:

1. deagle heat treated profitablitly calculatpr (generalisable to skin) expected value is calculated using number of skins redeemed (the confidence interval decreases as the number of skins redeemed increases, down to 50% at the end)

2. Make the profitability calculation easily generalisable with the values collected by an aiosteampy based gathererer which puts them into a json.

3. THis unique way of taking the income based on a custom confidence level that scales based on number of redeemed skins allows for a single final line graph which can be used in a like for like comparison with redeeming cases

This now has higher priority and also applies for charms etc. Its important to ensure that When redeeming only a few items at a time the value taken is with a higher confidence level whereas when redeeming many items in a week the expected value is taken outright.

Own Panel:

1. Build your own 20-man Casual hostsge pool panel. All accounts go near the hostsges and kill each other.

2. Here all accounts meet near the hostages where ct side gets 9 kills and t side gets 9 kills. The t side gets the last kill most of the time and wins.
In 3.5 of the rounds on avg the ct side shoots the last t side and then extracts getting the win. The match ends 8-7 with victor varying.

3. analysing joining text and occasionally running check and kick to kick intruders

documentation:

1. Function defintons for all functions including type hints.

2. A dedicated website with usage guides on all various aspects. IT will contain in depth guides on how to use
various parts of the repo and an overall guide on how it all works together. THings like overall daily usage
will also be covered (how an average farming day will look like when this is used in a production environment).

3. The website will be in its own dedicated documentation repo. With only the README.md, Roadmap.md and Roadmap_Packages.md being in the main repo.


GUI:

Use react for front end and fastapi for backend.


Daily usage for low scale farming:

all utils already running continuously on server
run farmlabs launcher and close it when its done.