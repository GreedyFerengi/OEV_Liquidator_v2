# OEV_Liquidator_v2 a Granary Finance liquidator bot for auctions using API3 OEV

This bot for Granary Finance will monitor open loans via the graph and submit OEV bids to update the price and liquidate!

1. Copy the env file to .env and fill out all the necessary information within it
2. Run the deployer.py script to deploy the smart contract
3. Go to the https://oev.api3.org/ frontend and deposit into the OEV Prepayment Depository
4. Run the smart contract unit tests to ensure .env params are correct and the contract functions complete
   - ensure there's about 100 FTM in your wallet, the tests will do some swaps for USDC and add to the smart contract so it can test swaps and flash loans, then it will withdraw it.
   - Run unit_tests.py
5. Ensure the flash loan transaction completed, as well as the oev price updated tranasaction. Successful unit tests will look like as follows:

```granary$ python3 unit_tests.py
0xF06E43DBe7c1318ab1CAb5747A42a32e0C3E9C88 on chain 250 bal 54.98200118511664 FL: 0xd35699edc77f359bDA7F1A6C8b2d7323B0bec311
swap successful, tx: 0x501b0412aa090f29c6ec8e4d46b50856060906f96dc7eabcfa3a080044575d43
wrap successful, tx: 0x6c370e2f25195558b1fee2b2b36438f20c0edf8e0be741fc509058e720b95da4
USDC sent, tx: 0xc8792ddead9bc752af4db8ef99683a157068b60c6f5dfb6de80fa4d14c513f3e
wFTM sent, tx: 0x9e6d68bb44d9e428bd2f76335c82890607fcbb539fc22c39720523476cf6661d
updated LP to 0x7220FFD5Dc173BA3717E47033a01d870f06E5284, tx: 0xf69c80087f0dcd79d4b3159243dd753b5238e467f90d528262f9450bd25067ad
reserve: 0x04068DA6C83AFCFA0e13ba15A6696662335D5B75, collateral: 0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83, amount: 1000000
FL contract collateral balance: 5.0
FL contract reserve balance: 2.0
flash loan completed for for 1000000: 0x1d9cc6c4274b22fe867e2580bda1a0c23f1f2e3e9ce9416b3e3056616d47f1b9
FL contract collateral balance: 0.0
FL contract reserve balance: 8.735883
withdrew USDC, tx: 0x9d1028e161da74db9c34b00afc86e3e3f29b67e985b332f56dc824acd951f27e
0xF06E43DBe7c1318ab1CAb5747A42a32e0C3E9C88 wins: ['2f26aab9-1321-40ec-94f1-f6e8105e2618']
bid placed with id:  {'id': 'e3beb766-ea97-4d0d-9334-81144122d6bd'}
0xF06E43DBe7c1318ab1CAb5747A42a32e0C3E9C88 wins: ['e3beb766-ea97-4d0d-9334-81144122d6bd']
updating oev price....
oev price updated tx: 0xa04fd4261df5375667ac16298d5c5ba89ddda7b17c2fbfc853d1bdd97b4146fc
```

6. Run the bot using execution.py

Due to the Multichain hack and the depletion of asset backing on Fantom, there have been limited opportunities to test this bot. A testnet setup is currently in development to validate it's efficacy. However, at the current time, the on-chain liquidation portion is largely untested. 
