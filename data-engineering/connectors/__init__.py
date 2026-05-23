from .forasna import ForasnaConnector
from .linkedin import LinkedInConnector
from .wuzzuf import WuzzufConnector

CONNECTORS = {
    "wuzzuf": WuzzufConnector,
    "forasna": ForasnaConnector,
    "linkedin": LinkedInConnector,
}
