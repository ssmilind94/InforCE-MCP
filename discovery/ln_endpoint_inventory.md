# LN OData endpoint inventory (GODREJ_DEV)

Base URL: `{iu}/{tenant}/LN/lnapi/odata/<service>/<resource>` — company via `X-Infor-LnCompany` header.

| Service | Entity sets | Operations |
|---|---|---|
| `tdapi.slsSalesOrder` | 44 | 4 |
| `tdapi.slsSalesContract` | 36 | 0 |
| `tdapi.purPurchaseOrder` | 58 | 0 |
| `tdapi.purPurchaseRequisition` | 19 | 0 |
| `tdapi.ipuItemPurchase` | 18 | 0 |
| `tdapi.isaItemSales` | 15 | 0 |
| `tcapi.comBusinessPartner` | 71 | 0 |
| `tcapi.comContact` | 5 | 0 |
| `tcapi.ibdItem` | 14 | 1 |
| `tiapi.sfcProductionOrder` | 21 | 3 |
| `tsapi.socServiceOrder` | 59 | 0 |
| `tsapi.ctmServiceContract` | 55 | 0 |
| `tpapi.pdmProject` | 13 | 0 |

## tdapi.slsSalesOrder

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Orders | entity set | SalesOrder | 102 | 45 |
| Lines | entity set | SalesOrder, Line, SequenceNumber | 152 | 41 |
| ActualDeliveryLines | entity set | SalesOrder, Line, SequenceNumber, ActualDeliveryLineSequenceNumber, InvoiceLine | 104 | 22 |
| BusinessPartners | entity set | BusinessPartner | 2 | 0 |
| Items | entity set | Item | 5 | 0 |
| Units | entity set | Unit | 2 | 0 |
| Projects | entity set | Project | 2 | 0 |
| SalesOrderTypes | entity set | SalesOrderType | 2 | 0 |
| Employees | entity set | Employee | 2 | 0 |
| Departments | entity set | Department | 2 | 0 |
| PriceStages | entity set | PriceStage | 2 | 0 |
| Sites | entity set | Site | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| ItemCodeSystems | entity set | ItemCodeSystem | 2 | 0 |
| Addresses | entity set | AddressCode | 8 | 0 |
| Contacts | entity set | Contact | 2 | 0 |
| Currencies | entity set | Currency | 2 | 0 |
| ExchangeRateTypes | entity set | ExchangeRateType | 2 | 0 |
| TaxClassifications | entity set | TaxClassification | 2 | 0 |
| LatePaymentSurcharges | entity set | LatePaymentSurcharge | 2 | 0 |
| CarriersLSPs | entity set | CarrierLSP | 2 | 0 |
| PriceLists | entity set | PriceList | 2 | 0 |
| DeliveryTerms | entity set | DeliveryTerms_ | 2 | 0 |
| PointsOfTitlePassages | entity set | PointOfTitlePassage | 2 | 0 |
| InstallmentPlans | entity set | InstallmentPlan | 2 | 0 |
| LinesOfBusiness | entity set | LineOfBusiness | 2 | 0 |
| Areas | entity set | Area | 2 | 0 |
| Reasons | entity set | Reason | 2 | 0 |
| PaymentTerms | entity set | PaymentTerms_ | 2 | 0 |
| Routes | entity set | Route | 2 | 0 |
| SalesAcknowledgments | entity set | SalesAcknowledgment | 2 | 0 |
| ChangeReasons | entity set | ChangeReason | 2 | 0 |
| ChangeTypes | entity set | ChangeType | 2 | 0 |
| SalesTypes | entity set | SalesType | 2 | 0 |
| ExtraIntrastatInfo | entity set | ExtraIntrastatInfo_ | 2 | 0 |
| ListGroups | entity set | ListGroup | 2 | 0 |
| FreightServiceLevels | entity set | FreightServiceLevel | 2 | 0 |
| Channels | entity set | Channel | 2 | 0 |
| Countries | entity set | Country | 2 | 0 |
| EffectivityUnits | entity set | EffectivityUnit | 2 | 0 |
| SalesChangeOrderSequenceNumbers | entity set | SalesOrder, ChangeOrderSequenceNumber | 3 | 0 |
| TaxCodesByCountry | entity set | Country, TaxCode | 3 | 0 |
| DeliveryPoints | entity set | DeliveryAddress, DeliveryPoint | 3 | 0 |
| CostComponents | entity set | CostComponent | 2 | 0 |
| CreateOrder | action | | | |
| CreateLine | action | | | |
| SimulateAdditionalCostLines | action | | | |
| CalculateLineAmounts | action | | | |

## tdapi.slsSalesContract

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Contracts | entity set | Contract | 46 | 30 |
| Lines | entity set | Contract, Line, SalesOffice | 83 | 34 |
| LineLogisticData | entity set | Contract, Line, SalesOffice, EffectiveDate | 50 | 7 |
| Prices | entity set | Contract, Line, SalesOffice, EffectiveDate | 10 | 3 |
| DeliveryLines | entity set | Contract, Line, SalesOffice, PlannedDeliveryDate | 9 | 3 |
| LinkedDocuments | entity set | Contract, Line, SalesOffice, LinkSequence | 8 | 4 |
| BusinessPartners | entity set | BusinessPartner | 2 | 0 |
| Addresses | entity set | AddressCode | 8 | 0 |
| Contacts | entity set | Contact | 2 | 0 |
| PaymentTerms | entity set | PaymentTerms_ | 2 | 0 |
| Currencies | entity set | Currency | 2 | 0 |
| Employees | entity set | Employee | 2 | 0 |
| TaxClassifications | entity set | TaxClassification | 2 | 0 |
| LatePaymentSurcharges | entity set | LatePaymentSurcharge | 2 | 0 |
| CarriersLSPs | entity set | CarrierLSP | 2 | 0 |
| DeliveryTerms | entity set | DeliveryTerms_ | 2 | 0 |
| PointsOfTitlePassages | entity set | PointOfTitlePassage | 2 | 0 |
| Departments | entity set | Department | 2 | 0 |
| SalesOrderTypes | entity set | SalesOrderType | 2 | 0 |
| TermsAndConditions | entity set | TermsAndConditionsID | 2 | 0 |
| Items | entity set | Item | 5 | 0 |
| EffectivityUnits | entity set | EffectivityUnit | 2 | 0 |
| Sites | entity set | Site | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| PriceGroups | entity set | PriceGroup | 2 | 0 |
| Units | entity set | Unit | 2 | 0 |
| PriceBooks | entity set | PriceBook | 2 | 0 |
| Countries | entity set | Country | 2 | 0 |
| Reasons | entity set | Reason | 2 | 0 |
| SalesAdditionalCostSets | entity set | CostsSet | 2 | 0 |
| TaxCodesByCountry | entity set | Country, TaxCode | 3 | 0 |
| DeliveryPoints | entity set | DeliveryAddress, DeliveryPoint | 3 | 0 |
| Channels | entity set | Channel | 2 | 0 |
| Patterns | entity set | Pattern | 2 | 0 |
| Companies | entity set | Company | 2 | 0 |
| BlockingDefinitions | entity set | BlockingDefinition | 2 | 0 |

## tdapi.purPurchaseOrder

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Orders | entity set | PurchaseOrder | 92 | 47 |
| Lines | entity set | PurchaseOrder, Line, Sequence | 163 | 53 |
| ActualReceipts | entity set | PurchaseOrder, Line, Sequence, ReceiptSequenceNumber | 43 | 9 |
| BusinessPartners | entity set | BusinessPartner | 2 | 0 |
| Employees | entity set | Employee | 2 | 0 |
| OrderTypes | entity set | PurchaseOrderType | 2 | 0 |
| Units | entity set | Unit | 2 | 0 |
| Items | entity set | Item | 5 | 0 |
| Departments | entity set | Department | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| Sites | entity set | Site | 2 | 0 |
| Manufacturers | entity set | Manufacturer | 2 | 0 |
| Currencies | entity set | Currency | 2 | 0 |
| Addresses | entity set | AddressCode | 8 | 0 |
| Contacts | entity set | Contact | 2 | 0 |
| PaymentTerms | entity set | PaymentTerms_ | 2 | 0 |
| ExchangeRateTypes | entity set | ExchangeRateType | 2 | 0 |
| LatePaymentSurcharges | entity set | LatePaymentSurcharge | 2 | 0 |
| CarriersLSPs | entity set | CarrierLSP | 2 | 0 |
| DeliveryTerms | entity set | DeliveryTerms_ | 2 | 0 |
| PointsOfTitlePassages | entity set | PointOfTitlePassage | 2 | 0 |
| LinesOfBusiness | entity set | LineOfBusiness | 2 | 0 |
| Areas | entity set | Area | 2 | 0 |
| Routes | entity set | Route | 2 | 0 |
| Reasons | entity set | Reason | 2 | 0 |
| PurchaseAcknowledgments | entity set | PurchaseAcknowledgment | 2 | 0 |
| ChangeReasons | entity set | ChangeReason | 2 | 0 |
| ChangeTypes | entity set | ChangeType | 2 | 0 |
| SelfBillingMethods | entity set | SelfBillingMethod | 2 | 0 |
| TaxClassifications | entity set | TaxClassification | 2 | 0 |
| LandedCostsClassifications | entity set | LandedCostsClassification | 2 | 0 |
| EffectivityUnits | entity set | EffectivityUnit | 2 | 0 |
| ItemCodeSystems | entity set | ItemCodeSystem | 2 | 0 |
| PriceStages | entity set | PriceStage | 2 | 0 |
| CostComponents | entity set | CostComponent | 2 | 0 |
| Projects | entity set | Project | 2 | 0 |
| Countries | entity set | Country | 2 | 0 |
| FreightServiceLevels | entity set | FreightServiceLevel | 2 | 0 |
| PurchaseTypes | entity set | PurchaseType | 2 | 0 |
| PaymentAgreements | entity set | PaymentAgreement | 2 | 0 |
| TargetPriceBooks | entity set | TargetPriceBook | 2 | 0 |
| TaxCodesByCountry | entity set | Country, TaxCode | 3 | 0 |
| ManufacturerPartNumbers | entity set | ManufacturerPartNumber, Manufacturer | 3 | 0 |
| InstallmentSchedulesSets | entity set | ScheduleSet | 2 | 0 |
| LinkedOrderLinesData | entity set | PurchaseOrder, Line, Sequence | 39 | 2 |
| BillsOfMaterials | entity set | PurchaseOrder, Line, Sequence, BOMLine | 6 | 3 |
| MaterialSupplyLines | entity set | PurchaseOrder, Line, Sequence, MaterialSequence | 42 | 13 |
| Confirmations | entity set | PurchaseOrder, Line, Sequence | 14 | 5 |
| LandedCostLines | entity set | BusinessObjectType, BusinessObjectOrigin, BusinessObject, BusinessObjectReference, LandedCostLineNumber | 89 | 34 |
| LandedCostTypes | entity set | LandedCostType | 2 | 0 |
| PriceLists | entity set | PriceList | 2 | 0 |
| DocumentMaterialPriceAgreements | entity set | BusinessObjectType, BusinessObject, BusinessObjectReference | 17 | 5 |
| MaterialExchanges | entity set | MaterialExchange | 2 | 0 |
| MaterialPriceAgreements | entity set | MaterialPriceAgreement | 2 | 0 |
| DocumentMaterialInformations | entity set | BusinessObjectType, BusinessObject, BusinessObjectReference, MaterialLine | 18 | 3 |
| Materials | entity set | Material | 2 | 0 |
| PayableReceipts | entity set | PurchaseOrder, LinePosition, LineSequence, ReceiptSequence, PayableReceiptSequence | 49 | 4 |
| SupplierStagePaymentLines | entity set | BusinessObjectType, BusinessObject, BusinessObjectReference, StagePaymentLine | 30 | 6 |

## tdapi.purPurchaseRequisition

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Requisitions | entity set | Requisition | 31 | 15 |
| Employees | entity set | Employee | 2 | 0 |
| Departments | entity set | Department | 2 | 0 |
| Sites | entity set | Site | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| Addresses | entity set | AddressCode | 8 | 0 |
| Lines | entity set | Requisition, Line | 42 | 17 |
| Projects | entity set | Project | 2 | 0 |
| Reasons | entity set | Reason | 2 | 0 |
| CostComponents | entity set | CostComponent | 2 | 0 |
| Currencies | entity set | Currency | 2 | 0 |
| Items | entity set | Item | 5 | 0 |
| EffectivityUnits | entity set | EffectivityUnit | 2 | 0 |
| ItemCodeSystems | entity set | ItemCodeSystem | 2 | 0 |
| Manufacturers | entity set | Manufacturer | 2 | 0 |
| Units | entity set | Unit | 2 | 0 |
| BusinessPartners | entity set | BusinessPartner | 2 | 0 |
| ManufacturerPartNumbers | entity set | ManufacturerPartNumber, Manufacturer | 3 | 0 |
| LinkedLineData | entity set | Requisition, Line | 21 | 2 |

## tdapi.ipuItemPurchase

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| ItemsPurchase | entity set | Item | 53 | 17 |
| Items | entity set | Item | 5 | 0 |
| Units | entity set | Unit | 2 | 0 |
| PriceGroups | entity set | PriceGroup | 2 | 0 |
| StatisticalGroups | entity set | StatisticalGroup | 2 | 0 |
| Currencies | entity set | Currency | 2 | 0 |
| TaxCodes | entity set | TaxCode | 2 | 0 |
| BusinessPartners | entity set | BusinessPartner | 2 | 0 |
| Employees | entity set | Employee | 2 | 0 |
| Companies | entity set | Company | 2 | 0 |
| Departments | entity set | Department | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| Manufacturers | entity set | Manufacturer | 2 | 0 |
| ManufacturerPartNumbers | entity set | ManufacturerPartNumber, Manufacturer | 3 | 0 |
| ItemsPurchaseBySite | entity set | Item, Site, PurchaseOffice | 49 | 14 |
| Sites | entity set | Site | 2 | 0 |
| ItemsPurchaseByPurchaseOffice | entity set | Item, Site, PurchaseOffice | 8 | 5 |
| Countries | entity set | Country | 2 | 0 |

## tdapi.isaItemSales

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| ItemsSales | entity set | Item | 37 | 16 |
| ItemsSalesBySalesOffice | entity set | Item, SalesOffice, Site | 34 | 15 |
| ItemsSalesBySite | entity set | Item, SalesOffice, Site | 7 | 4 |
| Items | entity set | Item | 5 | 0 |
| Units | entity set | Unit | 2 | 0 |
| PriceGroups | entity set | PriceGroup | 2 | 0 |
| StatisticalGroups | entity set | StatisticalGroup | 2 | 0 |
| CommissionRebateGroups | entity set | CommissionRebateGroup_ | 2 | 0 |
| Currencies | entity set | Currency | 2 | 0 |
| TaxCodes | entity set | TaxCode | 2 | 0 |
| BusinessPartners | entity set | BusinessPartner | 2 | 0 |
| Companies | entity set | Company | 2 | 0 |
| Sites | entity set | Site | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| Departments | entity set | Department | 2 | 0 |

## tcapi.comBusinessPartner

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| BusinessPartners | entity set | BusinessPartner | 56 | 30 |
| SoldtoBusinessPartners | entity set | SoldtoBusinessPartner | 78 | 30 |
| SoldtoBusinessPartnersByDepartment | entity set | SoldtoBusinessPartner, Department | 29 | 11 |
| ShiptoBusinessPartners | entity set | ShiptoBusinessPartner | 38 | 17 |
| ShiptoBusinessPartnersBySite | entity set | ShiptoBusinessPartner, Site | 12 | 10 |
| InvoicetoBusinessPartners | entity set | InvoicetoBusinessPartner, Department | 76 | 24 |
| InvoicetoBusinessPartnersByDepartment | entity set | InvoicetoBusinessPartner, Department | 76 | 24 |
| PaybyBusinessPartners | entity set | PaybyBusinessPartner, Department | 37 | 13 |
| PaybyBusinessPartnersByDepartment | entity set | PaybyBusinessPartner, Department | 37 | 12 |
| BuyfromBusinessPartners | entity set | BuyfromBusinessPartner | 67 | 24 |
| BuyfromBusinessPartnersByDepartment | entity set | BuyfromBusinessPartner, Department | 29 | 9 |
| ShipfromBusinessPartners | entity set | ShipfromBusinessPartner | 33 | 15 |
| ShipfromBusinessPartnersBySite | entity set | ShipfromBusinessPartner, Site | 14 | 10 |
| InvoicefromBusinessPartners | entity set | InvoicefromBusinessPartner, Department | 79 | 18 |
| InvoicefromBusinessPartnersByDepartment | entity set | InvoicefromBusinessPartner, Department | 79 | 18 |
| PaytoBusinessPartners | entity set | PaytoBusinessPartner, Department | 38 | 12 |
| PaytoBusinessPartnersByDepartment | entity set | PaytoBusinessPartner, Department | 38 | 11 |
| Addresses | entity set | AddressCode | 9 | 0 |
| Contacts | entity set | Contact | 2 | 0 |
| Languages | entity set | Language | 3 | 0 |
| Currencies | entity set | Currency | 3 | 0 |
| Companies | entity set | Company | 2 | 0 |
| Titles | entity set | Title | 2 | 0 |
| Signals | entity set | BusinessPartnerSignal | 2 | 0 |
| LinesOfBusiness | entity set | LineOfBusiness | 2 | 0 |
| BusinessPartnerTypes | entity set | BusinessPartnerType | 2 | 0 |
| CalendarCodes | entity set | CalendarCode | 2 | 0 |
| DeliveryTerms | entity set | DeliveryTerms | 2 | 0 |
| Channels | entity set | Channel | 2 | 0 |
| ListGroups | entity set | ListGroup | 2 | 0 |
| PriceLists | entity set | PriceList | 2 | 0 |
| Areas | entity set | Area | 2 | 0 |
| Employees | entity set | Employee | 2 | 0 |
| Priorities | entity set | Priority | 2 | 0 |
| IndustryCodes | entity set | IndustryCode | 2 | 0 |
| Masks | entity set | MaskCode | 2 | 0 |
| PointsOfTitlePassage | entity set | PointOfTitlePassage | 2 | 0 |
| SalesTerritories | entity set | SalesTerritory | 2 | 0 |
| DocumentSets | entity set | DocumentSet | 2 | 0 |
| NaturesOfSupply | entity set | NatureOfSupply | 2 | 0 |
| ServicesTrades | entity set | ServicesTrade | 2 | 0 |
| ItemGroups | entity set | ItemGroup | 2 | 0 |
| CarriersLSPs | entity set | CarrierLSP | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| FreightServiceLevels | entity set | FreightServiceLevel | 2 | 0 |
| Sites | entity set | Site | 2 | 0 |
| Departments | entity set | Department | 2 | 0 |
| ExchangeRateTypes | entity set | ExchangeRateType | 2 | 0 |
| BillingCycles | entity set | BillingCycle | 2 | 0 |
| TaxClassifications | entity set | TaxClassification | 2 | 0 |
| CreditInsuranceCompanies | entity set | CreditInsuranceCompany | 2 | 0 |
| LatePaymentSurcharges | entity set | LatePaymentSurcharge | 2 | 0 |
| InvoicingMethods | entity set | InvoicingMethodCode | 2 | 0 |
| ClosingMethods | entity set | ClosingMethod | 2 | 0 |
| PaymentTerms | entity set | PaymentTerms | 2 | 0 |
| CreditRatings | entity set | CreditRating | 2 | 0 |
| InstallmentPlans | entity set | InstallmentPlan | 2 | 0 |
| MatchCodes | entity set | MatchCode | 2 | 0 |
| InvoiceDeliveryMethods | entity set | InvoiceDeliveryMethod | 2 | 0 |
| PaymentAgreements | entity set | PaymentAgreement | 2 | 0 |
| SelfBillingMethods | entity set | SelfBillingMethod | 2 | 0 |
| ShiptoBySoldtoBusinessPartners | entity set | SoldtoBusinessPartner, ShiptoBusinessPartner | 2 | 0 |
| BankAccountsByPaybyBusinessPartner | entity set | PaybyBusinessPartner, BankAccountCode | 6 | 0 |
| TaxNumbersByBusinessPartner | entity set | BusinessPartner, BusinessPartnerTaxCountry, EffectiveDate | 14 | 0 |
| RegistrationsByBusinessPartner | entity set | BusinessPartner, Country, RegistrationType, Jurisdiction, EffectiveDate | 18 | 3 |
| BankAccountsByPaytoBusinessPartner | entity set | PaytoBusinessPartner, BankAccountCode | 12 | 0 |
| FiscalIdentificationsByBusinessPartner | entity set | BusinessPartner, BusinessPartnerTaxCountry, EffectiveDate | 7 | 0 |
| AddressesByBusinessPartner | entity set | BusinessPartner, Address | 3 | 1 |
| RegistrationTypes | entity set | RegistrationType | 2 | 0 |
| RegistrationCategories | entity set | RegistrationCategory | 2 | 0 |
| ReferenceBusinessPartners | entity set | BusinessPartner | 2 | 0 |

## tcapi.comContact

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Contacts | entity set | Contact | 58 | 4 |
| Languages | entity set | Language | 4 | 0 |
| BuyerRoles | entity set | BuyerRole | 2 | 0 |
| BusinessPartners | entity set | BusinessPartner | 3 | 0 |
| Addresses | entity set | AddressCode | 8 | 0 |

## tcapi.ibdItem

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Items | entity set | Item | 61 | 11 |
| ItemsBySites | entity set | Item, Site | 28 | 10 |
| Sites | entity set | Site | 5 | 0 |
| Units | entity set | Unit | 4 | 0 |
| ItemGroups | entity set | ItemGroup | 2 | 0 |
| UnitSets | entity set | UnitSet | 2 | 0 |
| ProductTypes | entity set | ProductType | 2 | 0 |
| ProductClasses | entity set | ProductClass | 2 | 0 |
| ProductLines | entity set | ProductLine | 2 | 0 |
| Manufacturers | entity set | Manufacturer | 3 | 0 |
| SelectionCodes | entity set | SelectionCode | 2 | 0 |
| Countries | entity set | Country | 6 | 0 |
| Departments | entity set | Department | 7 | 0 |
| ProductGroups | entity set | Site, ProductGroup | 3 | 0 |
| GetSegmentedItemKey | function | | | |

## tiapi.sfcProductionOrder

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Orders | entity set | Order | 86 | 11 |
| Operations | entity set | Order, Operation | 97 | 9 |
| MachineOperations | entity set | Order, Operation, MachineSequence | 28 | 5 |
| Materials | entity set | Order, Position | 56 | 4 |
| SerialHeaders | entity set | OrderType, Order, SchedulePosition, Product, SerialNumber | 9 | 3 |
| SerialComponents | entity set | OrderType, Order, SchedulePosition, Product, SerialNumber, Position, SequenceNumber | 13 | 1 |
| OrderDistributions | entity set | Order, DistributionLine, EffectivityUnit | 4 | 1 |
| Items | entity set | Item | 18 | 1 |
| EmployeesGeneral | entity set | Employee | 4 | 0 |
| WorkCenterPlanGroups | entity set | Site, PlanGroup | 5 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| Sites | entity set | Site | 2 | 0 |
| WorkCenters | entity set | WorkCenter | 4 | 1 |
| MachineTypes | entity set | MachineType | 2 | 0 |
| ReferenceOperations | entity set | ReferenceOperation, MachineType, Site, WorkCenter | 5 | 0 |
| MachineCapacityGroups | entity set | Site, WorkCenter, MachineType | 4 | 0 |
| MachineNumbers | entity set | Site, WorkCenter, MachineType, MachineNumber | 7 | 0 |
| Units | entity set | Unit | 4 | 0 |
| Departments | entity set | Department | 7 | 0 |
| SkillsByOperations | entity set | Order, Operation, Skill | 5 | 1 |
| Skills | entity set | Skill | 4 | 0 |
| CreateOperation | action | | | |
| LaborUtilizationByWeek | function | | | |
| DetermineMaterialShortage | function | | | |

## tsapi.socServiceOrder

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Orders | entity set | Order | 129 | 52 |
| InstallationGroups | entity set | InstallationGroup_ | 2 | 0 |
| BusinessPartners | entity set | BusinessPartner | 2 | 0 |
| Addresses | entity set | AddressCode | 8 | 0 |
| Contacts | entity set | Contact | 2 | 0 |
| LinesOfBusiness | entity set | LineOfBusiness | 2 | 0 |
| LatePaymentSurcharges | entity set | LatePaymentSurcharge | 2 | 0 |
| Currencies | entity set | Currency | 2 | 0 |
| DeliveryTerms | entity set | DeliveryTerms_ | 2 | 0 |
| Reasons | entity set | Reason | 2 | 0 |
| CarriersLSPs | entity set | CarrierLSP | 2 | 0 |
| PaymentTerms | entity set | PaymentTerms_ | 2 | 0 |
| PriceLists | entity set | PriceList | 2 | 0 |
| Projects | entity set | Project | 2 | 0 |
| Areas | entity set | Area | 2 | 0 |
| Routes | entity set | Route | 2 | 0 |
| Departments | entity set | Department | 2 | 0 |
| Employees | entity set | Employee | 2 | 0 |
| InstallmentPlans | entity set | InstallmentPlan | 2 | 0 |
| ServiceContracts | entity set | ServiceContract | 2 | 0 |
| SalesTypes | entity set | SalesType | 2 | 0 |
| PointsOfTitlePassage | entity set | PointOfTitlePassage | 2 | 0 |
| ExchangeRateTypes | entity set | ExchangeRateType | 2 | 0 |
| Sites | entity set | Site | 2 | 0 |
| TaxClassifications | entity set | TaxClassification | 2 | 0 |
| ReferenceActivitiesMasterRoutingOptions | entity set | ReferenceActivity | 2 | 0 |
| ServiceAreas | entity set | ServiceArea | 2 | 0 |
| ServiceTypes | entity set | ServiceType | 2 | 0 |
| Activities | entity set | Order, Activity | 109 | 39 |
| ActivityGroups | entity set | ActivityGroup | 2 | 0 |
| Items | entity set | Item | 5 | 0 |
| ServiceCars | entity set | ServiceCar | 2 | 0 |
| FieldChangeOrderHeaders | entity set | FieldChangeOrder | 2 | 0 |
| ResponseTypes | entity set | ResponseType | 2 | 0 |
| Priorities | entity set | Priority | 2 | 0 |
| Problems | entity set | Problem | 2 | 0 |
| Solutions | entity set | Solution | 2 | 0 |
| MeasurementTypes | entity set | MeasurementType | 2 | 0 |
| Positions | entity set | Position | 2 | 0 |
| ServiceKits | entity set | ServiceKit | 2 | 0 |
| Checklists | entity set | Checklist | 2 | 0 |
| CoverageTypes | entity set | CoverageType | 2 | 0 |
| MaterialCosts | entity set | Order, Line | 159 | 35 |
| CostComponents | entity set | CostComponent | 2 | 0 |
| Units | entity set | Unit | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| TaxCodes | entity set | TaxCode | 2 | 0 |
| PriceStages | entity set | PriceStage | 2 | 0 |
| ExtraIntrastatInfos | entity set | ExtraIntrastatInfo_ | 2 | 0 |
| Countries | entity set | Country | 2 | 0 |
| FreightServiceLevels | entity set | FreightServiceLevel | 2 | 0 |
| LaborCosts | entity set | Order, Line | 75 | 14 |
| Tasks | entity set | Task | 2 | 0 |
| LaborTypes | entity set | LaborType | 2 | 0 |
| LaborRateCodes | entity set | LaborRateCode | 2 | 0 |
| OtherCosts | entity set | Order, Line | 100 | 16 |
| TravelRateBooks | entity set | TravelRateBook | 2 | 0 |
| SerializedItems | entity set | Item, SerialNumber | 3 | 0 |
| ServiceEngineerAssignments | entity set | Origin, Order, LineNumber | 24 | 4 |

## tsapi.ctmServiceContract

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Contracts | entity set | ServiceContract | 75 | 35 |
| ContractChanges | entity set | ServiceContract, ContractChangeNumber | 22 | 11 |
| ConfigurationLines | entity set | ContractTerms, ConfigurationLine | 59 | 19 |
| CoverageTerms | entity set | TermID, ConfigurationLine, CoverageType, TermType, CoverageLine | 33 | 11 |
| ContractTypes | entity set | ContractType | 2 | 0 |
| Departments | entity set | Department | 2 | 0 |
| PriceLists | entity set | PriceList | 2 | 0 |
| EmployeesGenerals | entity set | Employee | 2 | 0 |
| Contacts | entity set | Contact | 2 | 0 |
| BusinessPartners | entity set | BusinessPartner | 2 | 0 |
| Addresses | entity set | AddressCode | 8 | 0 |
| LinesOfBusinesses | entity set | LineOfBusiness | 2 | 0 |
| Areas | entity set | Area | 2 | 0 |
| IndexationTemplates | entity set | IndexationTemplate | 2 | 0 |
| InstallmentTemplates | entity set | InstallmentTemplate | 2 | 0 |
| LatePaymentSurcharges | entity set | LatePaymentSurcharge | 2 | 0 |
| PaymentTermss | entity set | PaymentTerms_ | 2 | 0 |
| Currencies | entity set | Currency | 2 | 0 |
| ExchangeRateTypes | entity set | ExchangeRateType | 2 | 0 |
| Countries | entity set | Country | 2 | 0 |
| TaxClassifications | entity set | TaxClassification | 2 | 0 |
| TaxCodes | entity set | TaxCode | 2 | 0 |
| Reasons | entity set | Reason | 2 | 0 |
| SalesTypes | entity set | SalesType | 2 | 0 |
| Projects | entity set | Project | 2 | 0 |
| InstallationGroups | entity set | InstallationGroup_ | 2 | 0 |
| SerializedItems | entity set | Item, SerialNumber | 2 | 0 |
| ReferenceActivitiesMasterRoutingOptions | entity set | ReferenceActivity | 2 | 0 |
| CoverageTypes | entity set | CoverageType | 2 | 0 |
| ContractTemplates | entity set | ContractTemplate | 2 | 0 |
| ContractDiscountSchemes | entity set | ContractDiscountScheme | 2 | 0 |
| ServiceAreas | entity set | ServiceArea | 2 | 0 |
| Items | entity set | Item | 5 | 0 |
| SerializedItemGroups | entity set | SerializedItemGroup | 2 | 0 |
| CalendarCodes | entity set | CalendarCode | 2 | 0 |
| AvailabilityTypes | entity set | AvailabilityType | 2 | 0 |
| TravelingTerms | entity set | TermID, ConfigurationLine, CoverageType, TermType, CoverageLine, TravelingLine | 31 | 5 |
| CostComponents | entity set | CostComponent | 2 | 0 |
| MaterialTerms | entity set | TermID, ConfigurationLine, CoverageType, TermType, CoverageLine, MaterialLine | 40 | 6 |
| LaborTerms | entity set | TermID, ConfigurationLine, CoverageType, TermType, CoverageLine, LaborLine | 26 | 7 |
| HelpdeskTerms | entity set | TermID, ConfigurationLine, CoverageType, TermType, CoverageLine, HelpdeskLine | 40 | 11 |
| OtherTerms | entity set | TermID, ConfigurationLine, CoverageType, TermType, CoverageLine, OtherLine | 27 | 7 |
| UptimeTerms | entity set | TermID, ConfigurationLine, CoverageType, TermType, CoverageLine, UptimeLine | 15 | 3 |
| ServiceItemGroups | entity set | ServiceItemGroup | 2 | 0 |
| Tasks | entity set | Task | 2 | 0 |
| LaborRateCodes | entity set | LaborRateCode | 2 | 0 |
| LaborTypes | entity set | LaborType | 2 | 0 |
| Units | entity set | Unit | 2 | 0 |
| TimeIntervalsForInvoicings | entity set | InvoiceInterval | 2 | 0 |
| ResponseTypes | entity set | ResponseType | 2 | 0 |
| FixedPriceTerms | entity set | TermID, ConfigurationLine, FixedPriceLine | 9 | 4 |
| Installments | entity set | ServiceContract, InstallmentNumber | 34 | 3 |
| Revenues | entity set | ServiceContract, OriginContractChange, ConfigurationLine, PlannedYear, PlannedPeriod, RevenueLine | 25 | 3 |
| CostCoverageOverviews | entity set | ServiceContract, OriginContractChange, ConfigurationLine, CostLine | 19 | 3 |
| EstimatedContractRevenuesPerPeriods | entity set | ServiceContract, OriginContractChange, ConfigurationLine, Year, Period | 9 | 2 |

## tpapi.pdmProject

| Resource | Kind | Key | Properties | Navigations |
|---|---|---|---|---|
| Projects | entity set | Project | 164 | 12 |
| Elements | entity set | Project, Element | 56 | 4 |
| Activities | entity set | Project, Plan, Activity | 96 | 7 |
| Baselines | entity set | Project, Baseline | 10 | 1 |
| Addresses | entity set | AddressCode | 19 | 0 |
| Employees | entity set | Employee | 2 | 0 |
| ActivityRelationships | entity set | Project, Plan, FirstFreeNumber | 14 | 0 |
| ContractLines | entity set | Contract, ContractLine | 5 | 1 |
| Currencies | entity set | Currency | 2 | 0 |
| ProjectsGeneral | entity set | Project | 5 | 0 |
| Units | entity set | Unit | 2 | 0 |
| Warehouses | entity set | Warehouse | 2 | 0 |
| ActivityBaselines | entity set | Project, Baseline, Activity | 7 | 2 |
