"""Todas as rotas da API v2 num só lugar. Sem dependências internas."""

TOKEN = "/api.php/token"
V2 = "/api.php/v2"


class Routes:
    SESSION = f"{V2}/session"
    SWAGGER = f"{V2}/doc.json"  # público, mas exige a API habilitada

    TICKETS = f"{V2}/Assistance/Ticket"
    ARTICLES = f"{V2}/Knowledgebase/Article"
    ARTICLE_CATEGORIES = f"{V2}/Knowledgebase/Category"
    TICKET_CATEGORIES = f"{V2}/Dropdowns/ITILCategory"
    USERS = f"{V2}/Administration/User"
    ME_USER = f"{V2}/Administration/User/Me"  # exige scope extra

    @staticmethod
    def ticket(ticket_id: int) -> str:
        return f"{Routes.TICKETS}/{ticket_id}"

    @staticmethod
    def timeline(ticket_id: int) -> str:
        return f"{Routes.TICKETS}/{ticket_id}/Timeline"  # somente GET

    @staticmethod
    def followup(ticket_id: int) -> str:
        return f"{Routes.TICKETS}/{ticket_id}/Timeline/Followup"  # POST

    @staticmethod
    def article(article_id: int) -> str:
        return f"{Routes.ARTICLES}/{article_id}"

    @staticmethod
    def ticket_category(category_id: int) -> str:
        return f"{Routes.TICKET_CATEGORIES}/{category_id}"

    @staticmethod
    def user(user_id: int) -> str:
        return f"{Routes.USERS}/{user_id}"
