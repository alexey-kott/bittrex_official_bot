from block_io import BlockIo


version = 2
#key = "cafa-0b00-7728-6125" # production
key = "0208-1429-7ad2-1371" # TEST
pin = "78tnd62bsr1"
block_io = BlockIo(key, pin, version)
# print(block_io.get_balance())
# wallet = block_io.get_new_address(label = "new_wallet")
# print(wallet)
# print(block_io.get_address_balance(address = "2MtnM8aWxNz4MSW4hCaQG1X1VnQqoxM1ix6"))

print(block_io.get_new_address(label = 'test'))
# print(block_io.get_address_balance(label=328241232))