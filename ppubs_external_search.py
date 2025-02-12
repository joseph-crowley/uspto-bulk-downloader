# https://www.uspto.gov/sites/default/files/documents/Patent-Public-Search-Setting-Up-External-Searches-QRG.pdf

import logging
import urllib.parse
from typing import List, Optional, Literal

import requests
from pydantic import BaseModel, Field

# Set up logging.
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PatentPublicSearchQuery(BaseModel):
    """
    Data model for constructing a Patent Public Search URL.
    
    Attributes:
        q (str): The search query string.
        db (Optional[List[str]]): List of databases to search (e.g. ["USPAT"]).
            If not provided, defaults to all three databases.
        type (Literal["ids", "queryString"]): The search type. For patent
            publication number searches use "ids". Defaults to "queryString".
    """
    q: str = Field(..., description="Search query")
    db: Optional[List[str]] = Field(
        None,
        description=("Databases to search (e.g. ['USPAT', 'US-PGPUB']). "
                     "Defaults to all databases if omitted.")
    )
    type: Literal["ids", "queryString"] = Field(
        "queryString",
        description="Type of search; 'ids' for patent number queries."
    )

    BASE_URL: str = "https://ppubs.uspto.gov/pubwebapp/external.html"

    def build_url(self) -> str:
        """
        Construct the full URL for the Patent Public Search query.
        
        Returns:
            str: The complete URL.
        """
        params = {"q": self.q}
        if self.db:
            params["db"] = ",".join(self.db)
        params["type"] = self.type

        # Use urllib.parse.urlencode with safe characters to retain parentheses.
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params, safe='()')}"
        logger.debug("Built URL: %s", url)
        return url


class PatentPublicSearchAPI:
    """
    A lightweight API client to perform searches against Patent Public Search.
    """

    def __init__(self) -> None:
        self.session = requests.Session()

    def search(self, query: PatentPublicSearchQuery) -> requests.Response:
        """
        Execute the search using the given query model.
        
        Args:
            query (PatentPublicSearchQuery): The query model instance.
            
        Returns:
            requests.Response: The HTTP response object.
        
        Raises:
            requests.RequestException: If the HTTP request fails.
        """
        url = query.build_url()
        try:
            response = self.session.get(url)
            response.raise_for_status()
            logger.info("Request succeeded: %s", url)
            return response
        except requests.RequestException as exc:
            logger.error("Request failed: %s", exc)
            raise


# Helper functions to build queries for common use cases.

def patent_number_query(patent_number: str, pad: int = 7) -> PatentPublicSearchQuery:
    """
    Build a query for a single patent or pre-grant publication.
    """
    patent_number = patent_number.zfill(pad)
    q = f"({patent_number}).pn."
    return PatentPublicSearchQuery(q=q, type="ids")


def multiple_patent_numbers_query(patent_numbers: List[str], pad: int = 7) -> PatentPublicSearchQuery:
    """
    Build a query to search for multiple patent numbers.
    """
    normalized = [num.zfill(pad) for num in patent_numbers]
    q = f"({'|'.join(normalized)}).pn."
    return PatentPublicSearchQuery(q=q, type="ids")


def cpc_query(cpc: str) -> PatentPublicSearchQuery:
    """
    Build a query for a Cooperative Patent Classification (CPC).
    """
    q = f"{cpc.replace(' ', '')}.cpc."
    return PatentPublicSearchQuery(q=q)


def multiple_cpc_query(cpc_list: List[str]) -> PatentPublicSearchQuery:
    """
    Build a query for multiple CPC classifications, joined by OR.
    """
    q = f"({' OR '.join(c.replace(' ', '') for c in cpc_list)}).cpc."
    return PatentPublicSearchQuery(q=q)


def uspc_query(uspc: str) -> PatentPublicSearchQuery:
    """
    Build a query for a U.S. Patent Classification (USPC).
    """
    q = f"{uspc}.ccls."
    return PatentPublicSearchQuery(q=q)


def assignee_query(assignee: str) -> PatentPublicSearchQuery:
    """
    Build a query for patents assigned to a specific entity.
    """
    q = f"({assignee}).as."
    return PatentPublicSearchQuery(q=q)


def keywords_query(keywords: str) -> PatentPublicSearchQuery:
    """
    Build a query using keyword search.
    """
    return PatentPublicSearchQuery(q=keywords)


def multiple_categories_query(query1: str, query2: str) -> PatentPublicSearchQuery:
    """
    Combine two queries using an AND operator.
    """
    q = f"({query1}) AND ({query2})"
    return PatentPublicSearchQuery(q=q)


# Example usage:
if __name__ == "__main__":
    api = PatentPublicSearchAPI()

    # Example 1: Single patent number search.
    single_patent = patent_number_query("11235876")
    response = api.search(single_patent)
    print("Single Patent URL:")
    print(response.url)
    print(response.text[:200])

    # Example 2: Multiple patent numbers search.
    multi_patent = multiple_patent_numbers_query(["20200039559", "11225156"])
    response = api.search(multi_patent)
    print("\nMultiple Patents URL:")
    print(response.url)

    # Example 3: CPC classification search.
    cpc_search = cpc_query("B62D1/16")
    response = api.search(cpc_search)
    print("\nCPC Search URL:")
    print(response.url)

    # Example 4: Assignee search.
    assignee_search = assignee_query("Tesla")
    response = api.search(assignee_search)
    print("\nAssignee Search URL:")
    print(response.url)

