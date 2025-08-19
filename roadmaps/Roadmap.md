Roadmap:

   -5. When progress bar props shrink it a little so that info starts on next line

   -4. For m4a1s solitude and other high ends (taken from a specifc custom list or price limit) they do not wait for it to sell and keep lowering prices, instead they list them and if they are the most competitively priced item then it is marked as done and skipped so that items lister process can end in a timely manner. (list can be big, only liquids and low price items are sold with decreasing price strat) Note: It will also have the ability to spawn a new window that cannot be clsoed easily (to minimize accidental closes) (can be minimized to windows task list) and in that it checks every 45/60 mins that the items that we have listed are the lowest price on teh market, if so it does nothing and if not, it cancels and relists at the new lowest price. this process in the sperate tkinter window exits when all items are sold and so u do not have to keep checking htat the high tiers u are listing are at the best price.

   -3. Add m4a1s solitude to the redemption reccomender immediately (it takes risk into the calculation. use current total number of passes for decision)

   -2. Update steam items lister so that cheap items that are not within the armoury pass are allowed to be sold at greater loss

   -1. fix farm list updater having some failed updates (tenacity and steam api call with retry, some error)

   0. update stage 1 to include starting armoury pass farm job from within it (for now i still use standard to buy passes)

   when armoury pass famr job is created the redemption reccomender is also run

   logs injester uses number of stars (updated during stage 0 that also updates ingester db) alongside steam wallet balance and inventory value, logs injester run as part of stage 0 process 

   rework app.py to reflect this (having number of passes farmed, stema balance profit and total accounts value trached alongside cashout value)

   1. set public playwright (also acceptd new trade progected)

   2. cache redemption recommendation, Add charms to reccomender

   3. no account is pua and deserves full selling, update the items lister and remove pua= restriction

   4.   last v0.4:
      Daily once: (update C:\Users\Sivasai\Documents\GitHub\CaseFarm\utils\cache\data.json)
      pass_price updation using steamassets.com (items adder uses)
      if pass_price is updated does an emergency is_armoury=0 then notifies me and starts account region
      movement process and waits for my input. (full region movement involves creating the corresponding number of new accounts in new region, sending them trades from existing accounts to buy prime and armoury passes on them and setting them to is_armoury after trades are sent) This full region movement has not been automated yet.

      pua_threshold updation by getting prices dynamically. 

      Make it with streamlit.

      pass_prices, updated business sim, updated pua threshold, inventory value calculator, vac check on all accounts (defaults to false and not run), if pass prices update then trigger region switching sim with new data, update reccomender, revenue growth simulation direct. Make these files take the pass information from config.yaml 
      (all these added to end of stage 1)

   5. Also update the revenue growth simulation to reflect the new strategy and rented vms and dynamic price retrivals.
   
   6. include total cashout value in the ingester

   -- V0.9 --

   7. When jake adds pass buying and pass redeeming jobs, modify stage 1 to not just put up ticktick tasks but also actually create the farmlabs jobs and also update the ticktick tasks too. Cannot be owrked on till those 2 are added by Jake.
   
   8. A utility that tells the current value of all items if sold on csfloat using csfloat_api.
   
   9. Create the vac checker that uses the standard panel under the hood and updates the database.

   -- V1.0 --




Long term goals: (Start working on these after holidays)

   1. Automate market.csgo and csfloat

   2. Code the armoury account mover and checker

   3. Rewrite giftcard purchaser to make use of moogold and test the giftcard redeemer too. Also test out steam route tool on various networks with farmlabs.
   When making the moogold after checkout put a giant sleep then go to https://moogold.com/account/license-key/ to get the keys

   When sending >=$10, use remitano with bep chain. If sending less than $10 use binance pay. Ensure that currency is set to USD before any other operations. Here, we will not use any wallet balance, instead we immediately send what we need in real time.

   Another option to use rupees will also be available, when manager is built, this will be set automatically after checking that there is not enough balance. Both options (crypto and rupees) will be available to ensure maximum flexibility.

   -- V1.1 --

   4. Manager will be able to predict how many cases will come in the future and how many FUA accounts will be created, and based on that upcoming cases schedule which decides the upcoming FUA account schedule it sends items to main to sell on market.csgo. These items are automatically sold, the balance is withdrawn to binance and giftcards are purchased and used on the accounts so that they are ready by the time the cases are tradable and are ready to receive cases to sell them.

   5. The manager will also be able to predict not just future crpyto demand for giftcards but also future crypto demand for farmlabs and other such software.

   -- V1.2 --

   6. Update the scheduler to be fully autonomous after acquisition of the own pc, the scheduler also schedules prime farming for prime only group on Wednesday reset. The schedulr also does hourly balance updates

   7. Write a code to send ltc from your binance account to farmlabs balance.

   -- V1.3 --

   8. Code the market.csgo api data gatherer which can be used to gather market.csgo data. The manual items sender will be modified to make use of this (Eg suggestion would be these items which have good market.csgo prices and whose market.csgo prices sum up to 1.2-1.3x the money u need for giftcards, then manual items sender trades those items to main so that u can sell on market.csgo 10 days later.)

   9. Make the database secure by using sqlcipher and a SOTA key store. Once actual farming is no longer done on laptop, make it more secure. Improve overall repository security. Also do some repo cleanup.


   10. Code a New_Computer_Setup.py which will consist of .ps1 scripts and python code to make the computer ready to farm (manager, pc clients are all setup) and also configures hyper v and the VMs and all other aspects of the computer setup. It uses the GPU-VM1 vm as a base for setting up the vms. (Make after new pc)

   -- V2.0 -- reached

   11. Also consider formation of a company to manage all assets and for tax and accounting purposes.

   12. Setup a fully local farm in a separate building with 100s of computers physically connected to a main 
   computer that receive commands through the local network.


Shelved:
   1. Hook up load new accounts with the help of the updated steamguard.py and hook the other new accounts pages too.

   4. Hook backend for other files, for items lister make the stop button actually stop the listings on the backend and also make the logs stream properly for the items lister. ALso make it such that when u open view accounts page, all prime account have hteir inventories loaded beforehand (part of loading process)

   1. test the sendinput api and do some testing. Also make the skeleton of the firing solution generator. Also do some initial exploration into collision with friendlies and pathing and minor AI exploration in the new panel repo. Map out the creation of multiple different kill locations where all accounts are spread out and not clumped up and with each death on each round happening in a different location and character deaths not being clustered. WHen doing this, the clustering of the bot group will also be not very high. Multiple hardcoded solutiosn will have to be made for each map and a random solution is picked every round (Full time working on the panel has begun). Build the casual panel which is based on hardcoded movement and aiming scripts. Starting this work indicates that all other work has been finished and all other codes have now been integreted into the dasshboard and the clients. The dashboard's desktop client and the pc clients have achieved full feature parity with the web version. There is now no need to go into the codebase all work can be accomplished from the dashboard and all codes have been fully implemented in a production ready manner.

   2. The casual panel should be fully developed and productionized and all systems have been migrated away from farmlabs. (even including things like weekly drop collect, etc.) This is done after 400 FUA accounts.

   3. Finish implmeentation of the stage 2 process. Farm manager should now simultaneously handle both armoury pass and drop farming. Almost everything is now integrated into the manager and very little code is seen. Here, full automation of all processes is finally reached. (done towards end of stage 1)

   (Farmageddon and casual farm shelved)


Roadmap Notes:

   plan: Right now the plan is to simply keep farming using farmlabs into the significant future (2nd half of 2026). Then when the time comes when even losing 20 fully upgraded accounts (with 100 passes each  and in total worth around rs 25lakhs in steam balance) is not a big deal, then make the switch to the custom casual panel.

   Note: As of now, no ip or hwid or userdata bans are occurring. The only bans that are happening is manual bans where a reported lobby is checked and all suspicious bots within that lobby are banned. A proper casual panel when implemented using avast sandbox will require instant kick and very few disconnects. THis panel will be put into production when losing 20 accounts (max possible as there are no statistical bans or chain bans(see first line)) is no longer an issue.

   Note: When the sage full account banwave happened you traded multiple items from main to those accounts and main did not get banned even though those entire accounts got banned (not just vacced in cs2). This means that trading will be safe into the near future. Shift to using lyingcod491 as main storage account after a few more Indonesian/cheapest region armoury accounts are made.

   Hexogen gen will use smsactivate, alex fogur emails and captcha.run captcha or akami solver on discord, suborbit.al proxies (as u have balance on there).

   Use the otc section of @CryptoIndiaUnited on Telegram for large transactions.



Ego Goals: (beat them in terms of monthly profit)

   1. Beat Suici (140 accs as of 21-02-2025)
   
   2. Beat Katze (500 accs as of 6 May 2025)

   3. katze's friend benji / hunbenji (300 pcs doing ai farm)

   4. beat bhaviM who has 200 accounts


Farm growth stages:
1. 8 passes (30k per month) (1 vm on lpatop)
2. 20 passes (78k per month) (4vms on laptop)
3. 286 passes (1.35 cr/annum) (26 vms on server)
4. Multiple servers farming with each one earning 1.35cr/annum