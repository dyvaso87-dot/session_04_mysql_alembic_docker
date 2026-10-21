import unittest
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from access_control import seed_access_control
from database.database import Base
from graphql_schema import schema
from models.models import User


class FinancialModulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        seed_access_control(self.db)
        self.context = {"db": self.db, "current_user": None, "auth_error": None}

    def tearDown(self):
        self.db.close()

    def execute(self, document, variables=None, context=None):
        # Las operaciones reciben actorCompanyUserId (membresía con la que se prueba).
        if variables is not None and "actor" not in variables and hasattr(self, "actor"):
            variables = {**variables, "actor": self.actor}
        return schema.execute_sync(
            document, variable_values=variables, context_value=context or self.context
        )

    def prepare_company_and_admin(self):
        result = self.execute('mutation { createCompany(input: {name: "Empresa Financiera"}) { id } }')
        company_id = result.data["createCompany"]["id"]
        result = self.execute("""mutation($input: CreateCompanyAdminInput!) {
          createCompanyAdmin(input: $input) { id userId }
        }""", {"input": {"companyId": company_id, "name": "Admin Finanzas",
                             "email": "finanzas@example.com", "password": "ClaveSegura123"}})
        user = self.db.get(User, int(result.data["createCompanyAdmin"]["userId"]))
        self.context["current_user"] = user
        self.actor = result.data["createCompanyAdmin"]["id"]
        return company_id, user

    def test_minimum_data_transactions_and_validation_errors(self):
        company_id, user = self.prepare_company_and_admin()

        account_mutation = """mutation($input: CreateAccountInput!, $actor: ID!) {
          createAccount(input: $input, actorCompanyUserId: $actor) { id name accountType companyId }
        }"""
        account_ids = []
        for number, kind in enumerate(("DEBIT", "CASH", "SAVINGS"), 1):
            result = self.execute(account_mutation, {"input": {
                "companyId": company_id, "accountType": kind, "name": f"Cuenta {number}"
            }})
            self.assertIsNone(result.errors)
            account_ids.append(result.data["createAccount"]["id"])

        duplicate = self.execute(account_mutation, {"input": {
            "companyId": company_id, "accountType": "DEBIT", "name": "Cuenta 1"
        }})
        self.assertIn("Ya existe una cuenta", str(duplicate.errors))

        concept_mutation = """mutation($input: CreateConceptInput!, $actor: ID!) {
          createConcept(input: $input, actorCompanyUserId: $actor) { id name conceptType }
        }"""
        concept_ids = []
        concept_kinds = []
        for number in range(10):
            kind = "INCOME" if number < 5 else "EXPENSE"
            result = self.execute(concept_mutation, {"input": {
                "companyId": company_id, "conceptType": kind,
                "name": f"Concepto {kind} {number + 1}",
            }})
            self.assertIsNone(result.errors)
            concept_ids.append(result.data["createConcept"]["id"])
            concept_kinds.append(kind)

        assign_mutation = """mutation($input: AssignConceptToAccountInput!, $actor: ID!) {
          assignConceptToAccount(input: $input, actorCompanyUserId: $actor) { id accountId conceptId isActive }
        }"""
        for concept_id in concept_ids:
            result = self.execute(assign_mutation, {"input": {
                "accountId": account_ids[0], "conceptId": concept_id,
            }})
            self.assertIsNone(result.errors)
        duplicate_relation = self.execute(assign_mutation, {"input": {
            "accountId": account_ids[0], "conceptId": concept_ids[0],
        }})
        self.assertIn("ya está asignado", str(duplicate_relation.errors))

        relations = self.execute(
            f'query {{ accountConcepts(accountId: "{account_ids[0]}", actorCompanyUserId: "{self.actor}") {{ id isActive }} }}'
        )
        self.assertEqual(len(relations.data["accountConcepts"]), 10)

        transaction_mutation = """mutation($input: CreateTransactionInput!, $actor: ID!) {
          createTransaction(input: $input, actorCompanyUserId: $actor) {
            id amount transactionType capturedBy capturedByUser { email }
          }
        }"""
        transaction_ids = []
        for number in range(20):
            index = number % 10
            result = self.execute(transaction_mutation, {"input": {
                "accountId": account_ids[0], "conceptId": concept_ids[index],
                "transactionType": concept_kinds[index], "amount": str(number + 1),
            }})
            self.assertIsNone(result.errors)
            self.assertEqual(result.data["createTransaction"]["capturedBy"], str(user.id))
            transaction_ids.append(result.data["createTransaction"]["id"])

        # Una membresía que no existe no puede registrar movimientos.
        no_actor = self.execute(transaction_mutation, {"input": {
            "accountId": account_ids[0], "conceptId": concept_ids[0],
            "transactionType": "INCOME", "amount": "10",
        }, "actor": "999"})
        self.assertIn("no existe o está inactiva", str(no_actor.errors))

        negative = self.execute(transaction_mutation, {"input": {
            "accountId": account_ids[0], "conceptId": concept_ids[0],
            "transactionType": "INCOME", "amount": "0",
        }})
        self.assertIn("mayor que cero", str(negative.errors))
        incompatible = self.execute(transaction_mutation, {"input": {
            "accountId": account_ids[0], "conceptId": concept_ids[0],
            "transactionType": "EXPENSE", "amount": "10",
        }})
        self.assertIn("no es compatible", str(incompatible.errors))

        movements = self.execute(f'query {{ transactions(actorCompanyUserId: "{self.actor}", limit: 100) {{ id amount transactionType }} }}')
        self.assertEqual(len(movements.data["transactions"]), 20)
        balance = sum(
            Decimal(row["amount"]) * (1 if row["transactionType"] == "INCOME" else -1)
            for row in movements.data["transactions"]
        )
        self.assertNotEqual(balance, Decimal("0"))

        deleted = self.execute(
            f'mutation {{ deleteTransaction(id: "{transaction_ids[0]}", actorCompanyUserId: "{self.actor}") {{ id isActive }} }}'
        )
        self.assertFalse(deleted.data["deleteTransaction"]["isActive"])


if __name__ == "__main__":
    unittest.main()
