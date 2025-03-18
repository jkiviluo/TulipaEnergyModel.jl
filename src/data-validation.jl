export DataValidationException

"""
    DataValidationException

Exception related to data validation of the Tulipa Energy Model input data.
"""
mutable struct DataValidationException <: Exception
    error_messages::Vector{String}
end

function Base.showerror(io::IO, ex::DataValidationException)
    println(io, "DataValidationException: The following issues were found in the data:")
    for error_message in ex.error_messages
        println(io, "- " * error_message)
    end
end

"""
    validate_data!(connection)

Raises an error if the data is not valid.
"""
function validate_data!(connection)
    error_messages = String[]
    @timeit to "no duplicate rows" append!(error_messages, _validate_no_duplicate_rows!(connection))
    @timeit to "valid schema's oneOf constraints" append!(
        error_messages,
        _validate_schema_one_of_constraints!(connection),
    )
    @timeit to "only transport flows are investable" append!(
        error_messages,
        _validate_only_transport_flows_are_investable!(connection),
    )

    if length(error_messages) > 0
        throw(DataValidationException(error_messages))
    end

    return
end

function _validate_no_duplicate_rows!(connection)
    # It should be possible to add a primary key to the tables below to avoid this validation.
    # However, where to add this, and how to ensure it was added is not clear.
    duplicates = String[]
    for (table, primary_keys) in (
        ("asset", (:asset,)),
        ("asset_both", (:asset, :milestone_year, :commission_year)),
        ("asset_commission", (:asset, :commission_year)),
        ("asset_milestone", (:asset, :milestone_year)),
        ("assets_profiles", (:asset, :commission_year, :profile_type)),
        ("assets_rep_periods_partitions", (:asset, :year, :rep_period)),
        ("assets_timeframe_partitions", (:asset, :year)),
        ("assets_timeframe_profiles", (:asset, :commission_year, :profile_type)),
        ("flow", (:from_asset, :to_asset)),
        ("flow_both", (:from_asset, :to_asset, :milestone_year, :commission_year)),
        ("flow_commission", (:from_asset, :to_asset, :commission_year)),
        ("flow_milestone", (:from_asset, :to_asset, :milestone_year)),
        ("flows_profiles", (:from_asset, :to_asset, :year, :profile_type)),
        ("flows_rep_periods_partitions", (:from_asset, :to_asset, :year, :rep_period)),
        ("group_asset", (:name, :milestone_year)),
        ("profiles_rep_periods", (:profile_name, :year, :rep_period, :timestep)),
        ("profiles_timeframe", (:profile_name, :year, :period)),
        ("rep_periods_data", (:year, :rep_period)),
        ("rep_periods_mapping", (:year, :period, :rep_period)),
        ("timeframe_data", (:year, :period)),
        ("year_data", (:year,)),
    )
        append!(duplicates, _validate_no_duplicate_rows!(connection, table, primary_keys))
    end

    return duplicates
end

function _validate_no_duplicate_rows!(connection, table, primary_keys)
    keys_as_string = join(primary_keys, ", ")
    duplicates = String[]
    for row in DuckDB.query(
        connection,
        "SELECT $keys_as_string, COUNT(*) FROM $table GROUP BY $keys_as_string HAVING COUNT(*) > 1",
    )
        values = join(["$k=$(row[k])" for k in primary_keys], ", ")
        push!(duplicates, "Table $table has duplicate entries for ($values)")
    end

    return duplicates
end

function _validate_schema_one_of_constraints!(connection)
    error_messages = String[]
    for (table_name, table) in TulipaEnergyModel.schema, (col, attr) in table
        if haskey(attr, "constraints") && haskey(attr["constraints"], "oneOf")
            valid_types = attr["constraints"]["oneOf"]
            valid_types_string = join(["'$s'" for s in valid_types], ", ")
            for row in DuckDB.query(
                connection,
                "SELECT $col FROM $table_name WHERE $col NOT IN ($valid_types_string)",
            )
                push!(
                    error_messages,
                    "Table '$table_name' has bad value for column '$col': '$(row[1])'",
                )
            end
        end
    end

    return error_messages
end

function _validate_only_transport_flows_are_investable!(connection)
    error_messages = String[]

    for row in DuckDB.query(
        connection,
        "SELECT flow.from_asset, flow.to_asset,
        FROM flow
        LEFT JOIN flow_milestone
            ON flow.from_asset = flow_milestone.from_asset
            AND flow.to_asset = flow_milestone.to_asset
        WHERE flow.is_transport = FALSE
            AND flow_milestone.investable
        ",
    )
        push!(
            error_messages,
            "Flow ('$(row.from_asset)', '$(row.to_asset)') is investable but is not a transport flow",
        )
    end

    return error_messages
end
