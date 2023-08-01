from tools import *

class Deployer:
    def __init__(self, web3):
        self.name = self.__class__.__name__
        self.web3 = web3
        self.deployed_contract_objects = {}
        self.dir = os.getcwd()


    def deploy_contract(self, account, absolute_path, name, args=None):
        address, abi = deploy_returns_address_abi(absolute_path, self.web3, account.privateKey, args=args)
        contract = load_contract(self.web3, address, abi)
        self.deployed_contract_objects[name] = contract
        print(f'{name.lower()} contract deployed at : {address} ')
        return address, abi

    def run_deploys(self, account):
        print(f'{self.name} deploying contracts.....')

        name = "OevSearcherMulticallV1"
        absolute_path = self.dir + "/contracts/OevSearcherMulticallV1.sol"
        OSM, abi = self.deploy_contract(account, absolute_path, name, args=[Addresses.LP_POOL, Addresses.V2_SWAP])
        OSM_contract = load_contract(self.web3, OSM, abi)
        self.deployed_contract_objects = {name: OSM_contract}

        name = "flashLoanReceiver"
        absolute_path = self.dir + "/contracts/flashLoanReceiver.sol"
        FL, abi = self.deploy_contract(account, absolute_path, name, args=[Addresses.LP_POOL, Addresses.V2_SWAP])
        FL_contract = load_contract(self.web3, FL, abi)
        self.deployed_contract_objects[name] = FL_contract

        envfile = open(self.dir+"/.env", "a")
        envfile.write('\n' + f'FL_ADDRESS={FL}')
        envfile.close()

        function = OSM_contract.functions.transferOwnership(FL_contract.address)
        tx_params = get_tx_params(web3=self.web3, account=account, value=0, gas=1000000)
        tx = build_and_send_and_wait(self.web3, account, function, tx_params)
        print(f'OEV contract owner set to flashloan receiver, tx: {tx}')

        return self.deployed_contract_objects

    def run_deploy(self, account):
        print(f'{self.name} deploying contracts.....')
        name = "flashLoanfred"
        absolute_path = self.dir + "/fred.sol"
        FL, abi = self.deploy_contract(account, absolute_path, name, args=None)
        FL_contract = load_contract(self.web3, FL, abi)
        self.deployed_contract_objects[name] = FL_contract

if __name__ == "__main__":
    node = os.getenv("RPC")
    web3 = Web3(HTTPProvider(endpoint_uri=node, request_kwargs={'timeout': 100}))
    test_account = web3.eth.account.from_key(os.getenv("PRIV_KEY"))

    deploy = Deployer(web3)
    deploy.run_deploys(test_account)
