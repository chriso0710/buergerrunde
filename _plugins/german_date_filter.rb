module DateFilter
    MONTHS = %w(Januar Februar März April Mai Juni Juli August September Oktober November Dezember)
    def german_date(input)
        "#{input.strftime("%-d")}. #{MONTHS[input.strftime("%m").to_i - 1]} #{input.strftime("%Y")}"
    end

    def german_datetime(input)
        "#{german_date(input)} #{input.strftime("%H")}:#{input.strftime("%M")} Uhr"
    end
end

Liquid::Template.register_filter(DateFilter)