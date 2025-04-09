using DuckDB, TulipaIO, TulipaEnergyModel

input_dir = ARGS[1]
println(input_dir)
connection = DBInterface.connect(DuckDB.DB)
read_csv_folder(connection, input_dir; schemas = TulipaEnergyModel.schema_per_table_name)
energy_problem = run_scenario(connection)
