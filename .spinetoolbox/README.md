Steps to make Tulipa Toolbox project work

- Activate Python environment for Spine Toolbox
- Run Toolbox
- Open Tulipa folder as Toolbox project
- Select `tulipa db` item
- Click 'New Spine db' and save it to a location of choice
- Select `cscs from directory` item
- In Tool properties --> command line arguments --> Tool arguments
    - Point to a directory with Tulipa input data csvs
- Execute project

Later, if you e.g. create new scenarios in the database, re-loaing csv files will remove everything existing from the DB, so be careful.
