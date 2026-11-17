from planner.repo.export import assignment_csv, safe_cell


def test_ids_are_spreadsheet_safe():
    assert safe_cell("ACC-0001") == '="ACC-0001"'
    assert safe_cell("=2+2") == "'=2+2"
    csv = assignment_csv(
        [
            {
                "account_id": "ACC-0001",
                "display_name": "Helio Analytics",
                "derived_segment": "Enterprise",
                "status": "PROPOSED",
            }
        ]
    )
    # csv.writer escapes quotes; Excel still reads the formula ="ACC-0001"
    assert 'ACC-0001' in csv
    assert csv.splitlines()[1].startswith('"=""ACC-0001"""')
