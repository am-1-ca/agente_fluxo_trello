from google.adk.agents.llm_agent import Agent
from trello import TrelloClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os

# Load environment variables from .env file
load_dotenv()
TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_API_SECRET = os.getenv("TRELLO_API_SECRET")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")

# Function to get the current temporal context (e.g., current date and time)
def get_temporal_context():
    now = datetime.now() + timedelta(days=1)  # Adjusting for Trello's date handling
    return now.strftime("%Y-%m-%d %H:%M:%S")


# Function to retrieve the Trello client using the API key, secret, and token
def retrieve_trello_client():
    return TrelloClient(
        api_key=TRELLO_API_KEY,
        api_secret=TRELLO_API_SECRET,
        token=TRELLO_TOKEN
    )


# Function to add a task to Trello
def add_task_to_trello(task_name: str, task_description: str, due_date: str):
    client = retrieve_trello_client()

    # Logic to list boards
    client.list_boards()
    boards = client.list_boards()
    new_board = [b for b in boards if b.name == "DIO"][0]

    # Logic to Get the list where the card will be added
    lists = new_board.list_lists()
    my_list = [l for l in lists if l.name.upper() == "A fazer"][0]

    # Logic to create a card on Trello with the task name, description, and due date
    my_list.add_card(name=task_name, desc=task_description, due=due_date)


# Function to list all tasks for the day on Trello
def list_tasks_for_day(status: str = "all"):
    client = retrieve_trello_client()

    # Logic to list boards
    boards = client.list_boards()
    new_board = [b for b in boards if b.name == "DIO"][0]

    # Logic to Get the list where the card will be added
    lists = new_board.list_lists()

    if status.lower() == "all":
        filtered_cards = lists
    elif status.lower() == "a fazer":
        filtered_cards = [l for l in lists if l.name.upper() == "A fazer"]
    elif status.lower() == "em andamento":
        filtered_cards = [l for l in lists if l.name.upper() == "Em andamento"]
    elif status.lower() == "concluído":
        filtered_cards = [l for l in lists if l.name.upper() == "Concluído"]
    else:
        filtered_cards = lists

    tasks = []
    for l in filtered_cards:
        cards = l.list_cards()
        for card in cards:
            tasks.append({
                "name": card.name,
                "description": card.desc,
                "due_date": card.due,
                "status": l.name,
                "id": card.id
            })
    return tasks


# Logic to change the status of a task on Trello (e.g., from "To Do" to "In Progress" or "Done")
def update_task_status(task_name: str, new_status: str):
    try:
        client = retrieve_trello_client()

        # Logic to list boards
        boards = client.list_boards()
        new_board = [b for b in boards if b.name == "DIO"][0]
        
        # Logic to Get the list where the card will be added
        lists = new_board.list_lists()

        # Logic to map new_status to the corresponding list name
        status_to_list_name = {
            "A fazer": "A fazer",
            "Em andamento": "Em andamento",
            "Concluído": "Concluído"
        }

        list_name = status_to_list_name.get(new_status)
        if not list_name:
            raise ValueError(f"Invalid status: {new_status}. Valid statuses are: {', '.join(status_to_list_name.keys())}")
        
        target_list = next((l for l in lists if l.name.upper() == list_name.upper()), None)
        if not target_list:
            raise ValueError(f"List '{list_name}' not found on Trello board.")

        # Logic to find the card in all lists
        card_to_update = None
        original_list = None
        for l in lists:
            cards = l.list_cards()
            card_to_update = next((c for c in cards if c.name.lower() == task_name.lower()), None)
            if card_to_update:
                original_list = l
                break

        if not card_to_update:
            raise ValueError(f"Task '{task_name}' not found on Trello board.")
        
        # Logic to move the card to the new list
        card_to_update.change_list(target_list.id)
        return f"Task '{task_name}' status updated to '{new_status}'."
    except Exception as e:
        return str(e)


root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='''Você é um agente organizador de tarefas.
    Seu trabalho é receber uma tarefa do usuário, dividi-la em subtarefas menores e criar um cartão no Trello para cada subtarefa, incluindo seu nome e descrição.
    Você deve perguntar ao usuário quais são suas tarefas diárias e, em seguida, criar um cartão para cada tarefa no Trello.
    Você deve iniciar a conversa perguntando ao usuário quais são suas tarefas diárias e, em seguida, criar um cartão para cada tarefa no Trello.
    Sempre inicie a conversa perguntando sobre as tarefas diárias do usuário e informando a data analisada pela ferramenta get_temporal_context, já que o Trello inicia o mês com o dia 0, em vez de 1.
    Depois disso, pergunte ao usuário se ele deseja adicionar mais tarefas e, se ele disser que sim, pergunte sobre as novas tarefas e crie cartões para elas também no Trello.

    Suas funções:

    1. Adicionar novas tarefas, incluindo seus nomes e descrições, ao Trello.

    2. Listar todas as tarefas do dia no Trello ou filtrar por critérios específicos.
    3. Marque as tarefas como concluídas no Trello.
    4. Exclua as tarefas do Trello.
    5. Atualize o status da tarefa (por exemplo, de "A Fazer" para "Em Andamento" ou "Concluída") no Trello.
    6. Defina o contexto temporal das tarefas (por exemplo, hoje, amanhã, esta semana) no Trello para organizá-las adequadamente.''',
    tools=[get_temporal_context, add_task_to_trello, list_tasks_for_day, update_task_status],
    )
