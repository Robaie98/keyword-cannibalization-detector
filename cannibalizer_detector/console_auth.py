import argparse
import httplib2
from googleapiclient.discovery import build
from oauth2client import client
from oauth2client import file
from oauth2client import tools
from collections import defaultdict
from datetime import datetime, timedelta
import pandas as pd
import sys



def progressbar(it, prefix="", size=60, out=sys.stdout):
    count = len(it)
    def show(j):
        x = int(size*j/count)
        print("{}[{}{}] {}/{}".format(prefix, "#"*x, "."*(size-x), j, count), 
                end='\r', file=out, flush=True)
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    print("\n", flush=True, file=out)



class Authenticator:
    """ A class for starting, authenticating an API connection, and retrieving data from Google Cosnole API.
    
    """

    def __init__(self, api_name, api_version, client_secrets_path, site, scope=None) -> None:
        """Get a service that communicates to a Google API.

        Parameters
        ----------
        api_name: str
            The name of the api to connect to.
        api_version: str
            The api version to connect to.
        scope: list 
            strings representing the auth scopes to authorize for the connection.
        client_secrets_path: string
            A path to a valid client secrets file.
        """
        # Default arguments
        self.scope = ['https://www.googleapis.com/auth/webmasters.readonly'] if scope is None else scope 

        # Parse command-line arguments.
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            parents=[tools.argparser])
        flags = parser.parse_args([])

        # Set up a Flow object to be used if we need to authenticate.
        flow = client.flow_from_clientsecrets(
            client_secrets_path, scope=scope,
            message=tools.message_if_missing(client_secrets_path))

        # Prepare credentials, and authorize HTTP object with them.
        # If the credentials don't exist or are invalid run through the native client
        # flow. The Storage object will ensure that if successful the good
        # credentials will get written back to a file.
        storage = file.Storage(api_name + '.dat')
        credentials = storage.get()
        if credentials is None or credentials.invalid:
            credentials = tools.run_flow(flow, storage, flags)
        http = credentials.authorize(http=httplib2.Http())

        # Build the service object.
        self.service = build(api_name, api_version, http=http)
        self.site = site


    # Create Function to execute your API Request
    def execute_request(self, request):
        return self.service.searchanalytics().query(siteUrl=self.site, body=request).execute()


    def retrieve_data(self, dimension=None, operator=None, expression=None, start_date=None,  end_date=None, rowLimit=1000):
        """Query your search traffic data with filters and parameters that you define.
          
        The method returns zero or more rows grouped by the row keys (dimensions) that you define.
        You must define a date range of one or more days. The request arguments are explained in
        detail at https://developers.google.com/webmaster-tools/v1/searchanalytics/query.  

        Parameters
        ----------
        dimension: list 
            Zero or more dimensions to group results by. 
        operator: list 
            How your specified value must match (or not match) the dimension value for the row.
        expression: 
        start_date: str 
            Start date of the requested date range, in YYYY-MM-DD format, in PT time (UTC - 7:00/8:00).
        end_date: str
            End date of the requested date range, format is similar to start_date. 
        rowLimit: int 
            Valid range is 1 to 25,000; Default is 1,000] The maximum number of rows to return.

        Returns
        -------
        df: pd.DataFrame 
            Dataframe of queries' traffic statistics and website's urls 
        """
        # Default values
        today = datetime.now()
        end_date = today - timedelta(days=3) if end_date is None else end_date 
        start_date = today - timedelta(days=10) if start_date is None else start_date
        assert(start_date < end_date), f"End date, {end_date} is before start date, {start_date}."

        # Run the extraction
        scDict = defaultdict(list) # Create a dict to populate with extraction
        request = {
            'startDate': str(start_date),
            'endDate': str(end_date),
            'dimensions': ['date','page','query'],  #country, device, page, query, searchAppearance
            'dimensionFilterGroups': [{
                            'filters': [{
                                'dimension': dimension,              
                                'operator': operator,
                                'expression': expression
                            }]
                            }],
            'rowLimit': rowLimit
        }
        response = self.execute_request(request)
        try:
            for row in response['rows']:
                scDict['date'].append(row['keys'][0] or 0)    
                scDict['page'].append(row['keys'][1] or 0)
                scDict['query'].append(row['keys'][2] or 0)
                scDict['clicks'].append(row['clicks'] or 0)
        except Exception as e:
            print(f'An error occurred: {e}')

        # Add response to dataframe 
        df = pd.DataFrame(data = scDict)
        return df

    