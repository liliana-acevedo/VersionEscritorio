from supabase import create_client, Client

url : str = "https://tyacsmgagiisodzrmuxj.supabase.co"
key : str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5YWNzbWdhZ2lpc29kenJtdXhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk4MzI0MzQsImV4cCI6MjA3NTQwODQzNH0.iu6E5jNxKw4YKajXXnPPEtW3SFAF_U_a4PkQfEDyHmQ"

supabase: Client = create_client(url, key)