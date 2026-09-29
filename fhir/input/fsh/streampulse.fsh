Alias: $sp = https://mohitt31.github.io/streampulse/fhir/CodeSystem/streampulse
Alias: $ucum = http://unitsofmeasure.org

CodeSystem: StreamPulseCodes
Id: streampulse
Title: "StreamPulse local prototype codes"
Description: "Project-defined codes; not official OAH, HL7 or clinical terminology."
* ^caseSensitive = true
* ^experimental = true
* ^content = #complete
* #predicted-daily-mean-water-temperature "Predicted daily mean water temperature"
* #daily-mean-water-temperature "Daily mean water temperature"
* #pi90-low "Lower bound of empirical 90 percent prediction interval"
* #pi90-high "Upper bound of empirical 90 percent prediction interval"
* #p90-reference "Training-only seasonal 90th percentile reference"
* #watch "Unusual-warmth watch"
* #watch-on "Watch on"
* #watch-off "Watch off"
* #replay "Historical replay"
* #operational "Operational mode"
* #water_ridge_v1 "Water-history ridge v1"
* #weather_corr_v1 "Weather correction v1"
* #persistence "Persistence baseline"
* #climatology "Climatology baseline"
* #daily-aggregation "Aggregation of source-calendar hourly measurements"
* #n-hours "Number of hourly measurements"
* #n-quarters "Number of six-hour portions represented"
* #source-qualification "Source qualification codes; not FHIR result status"
* #confirm-temperature-and-measure-do "Confirm temperature and measure dissolved oxygen"
* #acknowledgement "Acknowledgement; not evidence sampling was completed"
* #forecast-generation "Forecast generation"
* #source-url "Source request URL"
* #synthetic-fixture "Synthetic forecast fixture"

ValueSet: StreamPulseRunModes
Id: run-modes
Title: "StreamPulse run modes"
Description: "Operational mode is a label, not certification of deployment readiness."
* StreamPulseCodes#replay
* StreamPulseCodes#operational

Extension: StreamPulseForecastOrigin
Id: forecast-origin
Title: "Forecast origin"
Description: "Simulated issuance time in replay mode; distinct from actual result publication time."
Context: Observation
* value[x] 1..1
* value[x] only dateTime

Extension: StreamPulseRunMode
Id: run-mode
Title: "Run mode"
Description: "Distinguishes reconstructed historical forecasts from operational results."
Context: Observation
* value[x] 1..1
* value[x] only code
* valueCode from StreamPulseRunModes (required)

Invariant: sp-interval
Description: "Prediction interval bounds must be ordered and include the point prediction."
Severity: #error
Expression: "component.where(code.coding.where(system = 'https://mohitt31.github.io/streampulse/fhir/CodeSystem/streampulse' and code = 'pi90-low').exists()).value.ofType(Quantity).value <= value.ofType(Quantity).value and value.ofType(Quantity).value <= component.where(code.coding.where(system = 'https://mohitt31.github.io/streampulse/fhir/CodeSystem/streampulse' and code = 'pi90-high').exists()).value.ofType(Quantity).value"

Profile: StreamPulseForecastObservation
Parent: http://hl7.eu/fhir/ig/oah/StructureDefinition/observation-indicators-oah
Id: streampulse-forecast-observation
Title: "StreamPulse predicted daily mean water temperature"
Description: "Experimental numerical forecast at an OAH Location; not a health RiskAssessment. Target dates retain source-calendar precision when timezone is unknown."
* ^experimental = true
* code = StreamPulseCodes#predicted-daily-mean-water-temperature
* effective[x] only Period
* effectivePeriod.start 1..1
* effectivePeriod.end 1..1
* issued 1..1
* method 1..1
* device 1..1
* device only Reference(StreamPulseModelDevice)
* derivedFrom 1..*
* derivedFrom only Reference(ObservationIndicatorsOah)
* value[x] 1..1
* value[x] only Quantity
* valueQuantity.system 1..1
* valueQuantity.system = "http://unitsofmeasure.org"
* valueQuantity.code 1..1
* valueQuantity.code = #Cel
* valueQuantity.value 1..1
* extension contains StreamPulseForecastOrigin named forecastOrigin 1..1 and StreamPulseRunMode named runMode 1..1
* component ^slicing.discriminator.type = #pattern
* component ^slicing.discriminator.path = "code"
* component ^slicing.rules = #open
* component contains piLow 1..1 and piHigh 1..1
* component[piLow].code = StreamPulseCodes#pi90-low
* component[piHigh].code = StreamPulseCodes#pi90-high
* component[piLow].value[x] only Quantity
* component[piHigh].value[x] only Quantity
* component[piLow].valueQuantity.system 1..1
* component[piLow].valueQuantity.system = "http://unitsofmeasure.org"
* component[piLow].valueQuantity.code 1..1
* component[piLow].valueQuantity.code = #Cel
* component[piLow].valueQuantity.value 1..1
* component[piHigh].valueQuantity.system 1..1
* component[piHigh].valueQuantity.system = "http://unitsofmeasure.org"
* component[piHigh].valueQuantity.code 1..1
* component[piHigh].valueQuantity.code = #Cel
* component[piHigh].valueQuantity.value 1..1
* obeys sp-interval

Profile: StreamPulseModelDevice
Parent: Device
Id: streampulse-model-device
Title: "StreamPulse versioned model software"
Description: "Software identity and source-code revision; not a medical-device approval claim."
* ^experimental = true
* deviceName 1..*
* version 1..*
* version.value 1..1
