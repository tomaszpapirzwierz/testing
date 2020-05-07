class Account:
"""
Sample class of a bank account
Excercise from Python 3 Udemy course
"""
    
    def __init__(self, owner, balance):
        self.owner = owner
        self.balance = balance
    
    def __str__(self):
        return f"Account owner: {self.owner} \nAccount balance: ${self.balance}"
    
    def deposit(self, deposit_amount):
        self.balance += deposit_amount
        print(f"{deposit_amount} has been placed into your account \nNew balance is: {self.balance}")
        
    def withdraw(self, withdraw_amount):
        if withdraw_amount > self.balance:
            print("Funds Unavailable!")
        else:
            self.balance -= withdraw_amount
            print(f"{withdraw_amount} has been withdrawn from your account \nNew balance is: {self.balance}")
            
