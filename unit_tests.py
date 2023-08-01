from deployer import *
from oev import *
from thegraph import fetchV2UnhealthyLoans

class UnitTesting:
    def __init__(self, web3, fl_address):
        self.name = self.__class__.__name__
        self.web3 = web3

        self.deployer = Deployer(web3)
        self.oev = OEV(web3)
        self.contract_objects = {}
        try:
            self.unhealthy_loans = fetchV2UnhealthyLoans()
        except:
            print(f'failure retrieving loans from the graph, going to keep going though')
        self.fulfilled_auctions = []

        fl_abi = json.loads(open('./contracts/storage/flashLoanReceiver_abi.json').read())
        self.contract_objects["flashLoanReceiver"] = load_contract(web3, fl_address, fl_abi)


    def deploy_contracts(self, account):
        self.contract_objects = self.deployer.run_deploys(account)

    def setups(self, test_account, live_account, send_tokens=False):
        version = None
        if self.web3.eth.chain_id == 1:
            version = 3
        if self.web3.eth.chain_id == 250:
            version = 2
        swap_ETH_for_ERC20(test_account, self.web3, Addresses.USDC, self.contract_objects["flashLoanReceiver"].address, amount=10 * 10 ** 18, version=version) ## get USDC for the test account send to FL receiver
        wrap(web3, live_account, Addresses.FTM, amount=10 * 10 ** 18)
        if send_tokens:
            if test_account != live_account:
                tx_params = get_tx_params(web3=self.web3, account=test_account, value=1*10**18, gas=1000000, to=live_account.address)
                send_and_wait(self.web3, test_account, tx_params)
            usdc_obj = load_contract(web3=web3, abi=erc20_abi, address=Addresses.USDC)
            function = usdc_obj.functions.transfer(self.contract_objects["flashLoanReceiver"].address, int(2000000))
            tx_params = get_tx_params(web3=web3, account=live_account, value=0, gas=1000000)
            tx = build_and_send_and_wait(web3, live_account, function, tx_params)
            print(f'USDC sent, tx: {tx}')
            wftm_obj = load_contract(web3=web3, abi=weth_abi, address=Addresses.FTM)
            function = wftm_obj.functions.transfer(self.contract_objects["flashLoanReceiver"].address, int(5 * 10 ** 18))
            tx_params = get_tx_params(web3=web3, account=live_account, value=0, gas=1000000)
            tx = build_and_send_and_wait(web3, live_account, function, tx_params)
            print(f'wFTM sent, tx: {tx}')

    def update_lp(self, account):
        contract = self.contract_objects["flashLoanReceiver"]
        function = contract.functions.updateLendingPool(Addresses.LP_POOL)
        tx_params = get_tx_params(web3=web3, account=account, value=0, gas=1000000)
        tx = build_and_send_and_wait(web3, account, function, tx_params)
        print(f'updated LP to {Addresses.LP_POOL}, tx: {tx}')

    def withdraw_tokens(self, account, token):
        contract = self.contract_objects["flashLoanReceiver"]
        function = contract.functions.withdrawERC20(token)
        tx_params = get_tx_params(web3=web3, account=account, value=0, gas=1000000)
        tx = build_and_send_and_wait(web3, account, function, tx_params)
        print(f'withdrew USDC, tx: {tx}')

    def flash_loan_test(self, account, reserve, collateral, amount=100000, user="0x0000000000000000000000000000000000000069"):
        fl_contract = self.contract_objects["flashLoanReceiver"]
        print(f'reserve: {reserve}, collateral: {collateral}, amount: {amount}')
        function = fl_contract.functions.myFlashLoanCall([reserve], [amount], [0], collateral + user.replace("0x", ""))
        tx_params = get_tx_params(web3=web3, account=account, value=0, gas=1000000)
        print(f'FL contract collateral balance: {erc20_balance(fl_contract.address, load_contract(web3, collateral, erc20_abi))}')
        print(f'FL contract reserve balance: {erc20_balance(fl_contract.address, load_contract(web3, reserve, erc20_abi))}')
        tx = build_and_send_and_wait(web3, account, function, tx_params)
        print(f'flash loan completed for for {amount}: {tx}')
        print(f'FL contract collateral balance: {erc20_balance(fl_contract.address, load_contract(web3, collateral, erc20_abi))}')
        print(f'FL contract reserve balance: {erc20_balance(fl_contract.address, load_contract(web3, reserve, erc20_abi))}')

    # not used
    def deposit_to_oev(self, account, mainnet_rpc, amount=1000000):
        token = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        web3 = Web3(HTTPProvider(endpoint_uri=mainnet_rpc, request_kwargs={'timeout': 100}))
        contract = load_contract(web3, os.getenv("PREPAYMENT_DEPOSIT_ADDRESS"), api3_prepayment_depository_abi)
        tx = approve_erc20(web3, account, token, contract.address, amount)
        if tx:
            print(f'OEV deposit approved to spend {amount} {token} for {account.address}')
        swap_ETH_for_ERC20(account, web3, Addresses.USDC, account.address)
        function = contract.functions.deposit(account.address, amount)
        tx_params = get_tx_params(web3=web3, account=account, value=0, gas=100000)
        tx = build_and_send_and_wait(web3, account, function, tx_params)
        print(f'deposited USDC to OEV contract, tx: {tx}')
        self.oev.oev_status(live_account)

    def place_oev_bid(self, live_account):
        value = .32 * 10**18
        bid = self.oev.place_bid(live_account, self.contract_objects["flashLoanReceiver"].address, value, dAppProxyAddress=Addresses.FTMoevDatafeedProxy)
        print(f'bid placed with id:  {bid}')
        return bid

    def check_oev_wins(self, live_account):
        wins = self.oev.winning_bids(live_account)
        if wins:
            print(f"{live_account.address} wins: {wins['winningBidIds']}")
            return wins
        else:
            print(f"{live_account.address} wins: no winning bids")
            return False

    def update_oev_price(self, live_account):
        tx = self.oev.update_prices(live_account, self.contract_objects["flashLoanReceiver"], Addresses.Api3ServerV1)
        print(f'oev price updated tx: {tx}')
        return tx

    def do_liquidation(self, live_account, amount, user, reserve, collateral):
        contract = self.contract_objects["flashLoanReceiver"]
        wins = self.check_oev_wins(live_account)
        encodedUpdateTransaction = wins["encodedUpdateTransaction"]
        nativeCurrencyAmount = int(wins["nativeCurrencyAmount"])
        args = ([Addresses.LP_POOL], [encodedUpdateTransaction], [nativeCurrencyAmount], [reserve], [amount], [0], collateral + user.replace("0x", ""))
        function = contract.functions.doLiquidation(*args)
        tx_params = get_tx_params(web3=web3, account=live_account, value=0, gas=1000000)
        tx = build_and_send_and_wait(web3, live_account, function, tx_params)
        print(f'liquidation successful: {tx}')

    def run_live_tests(self, account):
        print(f'{account.address} on chain {self.web3.eth.chain_id} bal {web3.eth.getBalance(account.address)/10**18} FL: {os.getenv("FL_ADDRESS")}')
        # self.deploy_contracts(account)
        self.setups(live_account, live_account, True)
        self.update_lp(account)
        self.flash_loan_test(account, Addresses.USDC, Addresses.FTM, amount=1000000)
        self.withdraw_tokens(account, Addresses.USDC)
        self.check_oev_wins(live_account)
        self.place_oev_bid(live_account)
        time.sleep(60)
        self.check_oev_wins(live_account)
        self.update_oev_price(live_account)

    def test_for_liq(self, live_account):
        loan_data = self.unhealthy_loans
        for loan in loan_data:
            user = loan.user
            collateral = loan.collateralToken
            reserve = loan.borrowToken
            loan_amount = 0
            for item in loan.borrowReserve:
                if item[1] == loan.borrowToken:
                    loan_amount = int(item[2])
            self.do_liquidation(live_account, loan_amount, user, reserve, collateral)

    def bid_spammer(self, live_account):
        self.check_oev_wins(live_account)
        self.place_oev_bid(live_account)
        time.sleep(60)
        self.update_oev_price(live_account)


if __name__ == "__main__":
    node = os.getenv("RPC")
    web3 = Web3(HTTPProvider(endpoint_uri=node, request_kwargs={'timeout': 100}))
    test_account = web3.eth.account.from_key(os.getenv("TEST_KEY"))
    live_account = web3.eth.account.from_key(os.getenv("PRIV_KEY"))

    executor = UnitTesting(web3, os.getenv("FL_ADDRESS"))
    executor.run_live_tests(live_account)

