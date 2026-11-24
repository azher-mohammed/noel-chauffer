/* Noel Chauffer — driver app logic.
   While prices are paused the driver sees NO money figure at all:
   a job shows pickup, drop-off and time only. A job offer stays on
   screen until the driver
   accepts or declines it — it never expires on its own — and a tone
   repeats for 30 seconds when a new offer arrives so the driver
   knows a job came in, stopping when he answers or the offer goes.
   Job offers reach only drivers whose vehicle class matches the
   booking's class (Business Class / Business SUV); hourly rides reach
   every driver, available or offline. */
(function () {
  "use strict";

  var TOKEN_KEY = "noel_driver_token";
  /* Offer IDs the driver has already been alerted to, kept across
     page refreshes so a refresh never re-rings an old offer — and so
     a genuinely new offer still rings on the very first poll. */
  var SEEN_OFFERS_KEY = "noel_seen_offers";
  var MAX_SEEN_OFFERS = 200;
  /* A new offer rings for 30 seconds: the chime pattern repeats
     until the driver accepts or declines, the offer disappears, or
     the 30 seconds are up. */
  var TONE_DURATION_MS = 30000;
  var TONE_REPEAT_MS = 1500;
  var FILE_FIELDS = [
    "profile_photo",
    "doc_dmv_license",
    "doc_tlc_license",
    "doc_fh1",
    "doc_registration",
    "doc_inspection",
    "doc_vehicle_permit",
    "doc_nj_qualification",
    "doc_nj_municipal_license",
    "doc_nj_limo_registration",
    "doc_nj_insurance",
    "doc_vehicle_registration",
    "doc_insurance_card",
    "doc_al_certificate",
    "doc_al_form_e",
    "doc_ca_tcp_permit",
    "doc_ca_driver_statement",
    "doc_ca_commercial_registration",
    "doc_ca_inspection_declaration",
    "doc_co_ll_permit",
    "doc_co_inspection",
    "doc_co_form_e",
    "doc_ct_livery_permit",
    "doc_de_certificate",
    "doc_de_limo_registration",
    "doc_de_inspection",
    "doc_dc_drivers_record",
    "doc_dc_ssc",
    "doc_dc_residency",
    "doc_dc_medical_form",
    "doc_dc_face_id",
    "doc_dc_public_vehicle_license",
    "doc_dc_inspection",
    "doc_ga_carrier_certificate",
    "doc_ga_insurance_certificate",
    "doc_hi_carrier_certificate",
    "doc_hi_vehicle_inventory",
    "doc_hi_tax_clearance",
    "doc_ks_certificate",
    "doc_ky_limousine_certificate",
    "doc_ky_vehicle_license",
    "doc_ky_inspection",
    "doc_me_registration",
    "doc_me_jb_filing",
    "doc_md_for_hire_license",
    "doc_md_inspection_certificate",
    "doc_mi_carrier_license",
    "doc_mn_permit",
    "doc_mn_inspection",
    "doc_mn_form_e",
    "doc_mo_authority",
    "doc_ne_medical_certificate",
    "doc_ne_carrier_authority",
    "doc_nv_drivers_permit",
    "doc_nv_cpcn",
    "doc_nm_inspection",
    "doc_oh_livery_registration",
    "doc_pa_driving_history",
    "doc_pa_criminal_history",
    "doc_pa_certificate",
    "doc_pa_inspection",
    "doc_pa_form_e",
    "doc_ri_operator_license",
    "doc_ri_driving_record",
    "doc_ri_criminal_record",
    "doc_sc_driving_record",
    "doc_sc_charter_certificate",
    "doc_sc_ls_registration",
    "doc_sc_form_e",
    "doc_tn_citizenship_proof",
    "doc_tn_residency_proof",
    "doc_va_authority",
    "doc_va_title",
    "doc_va_for_hire_registration",
    "doc_va_authority_registration",
    "doc_wa_medical_certificate",
    "doc_wa_driving_record",
    "doc_wa_carrier_license",
    "doc_wa_vehicle_certificate",
    "doc_wa_chauffeur_addendum",
    "doc_wa_fh_registration",
    "doc_wa_inspection_report",
    "doc_wa_insurance_certificate"
  ];
  var DOC_LABELS = {
    profile_photo: "Profile Picture",
    doc_dmv_license: "DMV driving license",
    doc_tlc_license: "TLC License",
    doc_fh1: "FH-1 Insurance Card",
    doc_registration: "Commercial Vehicle Registration",
    doc_inspection: "NYS DMV Inspection",
    doc_vehicle_permit: "TLC-for-hire Vehicle Permit",
    doc_nj_qualification: "MVC Letter of Qualification",
    doc_nj_municipal_license: "Municipal License to Operate",
    doc_nj_limo_registration: "Limousine Vehicle Registration",
    doc_nj_insurance: "Insurance Certificate",
    doc_vehicle_registration: "Vehicle Registration",
    doc_insurance_card: "Insurance Card",
    doc_al_certificate: "Certificate of Intrastate Authority (APSC)",
    doc_al_form_e: "Form E (Insurance Filing)",
    doc_ca_tcp_permit: "Charter-Party Carrier (TCP) Certificate/Permit (Class A, B or P)",
    doc_ca_driver_statement: "Driver Statement of Application (Form PL739-A)",
    doc_ca_commercial_registration: "Commercial Vehicle Registration (Form PL664)",
    doc_ca_inspection_declaration: "Vehicle Inspection Declaration (Form PL668)",
    doc_co_ll_permit: "Luxury Limousine (LL) Permit",
    doc_co_inspection: "Vehicle Inspection",
    doc_co_form_e: "Form E (Insurance Filing)",
    doc_ct_livery_permit: "Livery Permit (CT DOT)",
    doc_de_certificate: "Certificate of Public Convenience and Necessity",
    doc_de_limo_registration: "Limousine Registration",
    doc_de_inspection: "Vehicle Inspection",
    doc_dc_drivers_record: "Driver's Record",
    doc_dc_ssc: "Social Security Card",
    doc_dc_residency: "Proof of Residency",
    doc_dc_medical_form: "Medical History / Physical Examination Form",
    doc_dc_face_id: "For-Hire Operators (Face ID) License",
    doc_dc_public_vehicle_license: "Public Vehicle-for-Hire License",
    doc_dc_inspection: "DMV Inspection",
    doc_ga_carrier_certificate: "Limousine Carrier Certificate (Georgia DPS)",
    doc_ga_insurance_certificate: "Certificate of Insurance",
    doc_hi_carrier_certificate: "Motor Carrier Certificate / Permit (Form 92-001)",
    doc_hi_vehicle_inventory: "Vehicle Inventory List (Exhibit B)",
    doc_hi_tax_clearance: "Tax Clearance Certificate",
    doc_ks_certificate: "Certificate of Convenience and Necessity (KCC)",
    doc_ky_limousine_certificate: "Limousine Certificate",
    doc_ky_vehicle_license: "Motor Carrier Vehicle License",
    doc_ky_inspection: "Vehicle Inspection",
    doc_me_registration: "Vehicle Registration with HIRE Plates (Class TX)",
    doc_me_jb_filing: "Insurance Certificate for For-Hire Passenger Vehicle (JB Filing)",
    doc_md_for_hire_license: "Passenger-for-Hire Driver's License (PSC)",
    doc_md_inspection_certificate: "Vehicle Inspection Certificate",
    doc_mi_carrier_license: "Limousine Carrier License",
    doc_mn_permit: "Limousine Service Permit (MnDOT)",
    doc_mn_inspection: "Vehicle Inspection",
    doc_mn_form_e: "Form E (Insurance Filing)",
    doc_mo_authority: "Motor Carrier Operating Authority (MoDOT)",
    doc_ne_medical_certificate: "Medical Certificate",
    doc_ne_carrier_authority: "Common / Contract Carrier Authority (PSC)",
    doc_nv_drivers_permit: "Driver's Permit (NTA)",
    doc_nv_cpcn: "Certificate of Public Convenience and Necessity (CPCN)",
    doc_nm_inspection: "Vehicle Inspection",
    doc_oh_livery_registration: "Vehicle Registration (Livery Plates)",
    doc_pa_driving_history: "Driving History (3-Year Record)",
    doc_pa_criminal_history: "Criminal History Record",
    doc_pa_certificate: "Certificate of Public Convenience (PUC)",
    doc_pa_inspection: "Vehicle Inspection",
    doc_pa_form_e: "Form E (Insurance Filing)",
    doc_ri_operator_license: "Taxi-LPMV-PMV Operator's License",
    doc_ri_driving_record: "Driving Record",
    doc_ri_criminal_record: "Record of Criminal Convictions",
    doc_sc_driving_record: "Certified Driving Record (3 Years)",
    doc_sc_charter_certificate: "Class C Charter Certificate",
    doc_sc_ls_registration: "Vehicle Registration (LS Plates)",
    doc_sc_form_e: "Form E (Insurance Filing)",
    doc_tn_citizenship_proof: "Proof of Citizenship or Lawful Permanent Residency",
    doc_tn_residency_proof: "Proof of Tennessee Residency",
    doc_va_authority: "For-Hire Intrastate Operating Authority",
    doc_va_title: "Vehicle Title (Virginia)",
    doc_va_for_hire_registration: "For-Hire Vehicle Registration",
    doc_va_authority_registration: "Operating Authority Registration",
    doc_wa_medical_certificate: "Medical Examiner's Certificate",
    doc_wa_driving_record: "Driving Record",
    doc_wa_carrier_license: "Limousine Carrier License",
    doc_wa_vehicle_certificate: "Limousine Vehicle Certificate",
    doc_wa_chauffeur_addendum: "Limousine Carrier Chauffeur Addendum",
    doc_wa_fh_registration: "Vehicle Registration Certificate (Use Class F/H)",
    doc_wa_inspection_report: "Vehicle Inspection Report",
    doc_wa_insurance_certificate: "Certificate of Insurance",
    doc_dallas_commercial_insurance: "Commercial Insurance Certificate",
    doc_dallas_driver_permit: "Dallas Driver Permit",
    doc_dallas_limo_permit: "City Limo Permit (Dallas / Fort Worth)",
    doc_buffalo_taxi_driver_license: "City of Buffalo Taxi Driver License",
    doc_buffalo_insurance_certificate: "Certificate of Automobile Liability Insurance",
    doc_buffalo_inspection_report: "Vehicle Inspection Report",
    doc_rochester_taxi_driver_license: "City of Rochester Taxicab Driver License",
    doc_rochester_hack_certificate: "Taxicab License Certificate (Hack Plate Certificate)",
    doc_rochester_insurance: "Proof of Insurance",
    doc_syracuse_hack_license: "Taxi (Hack) License",
    doc_syracuse_ground_transportation: "Ground Transportation License",
    doc_syracuse_for_hire_insurance: "Proof of For-Hire Insurance",
    doc_wctlc_driver_permit: "WCTLC For-Hire Driver Permit",
    doc_wctlc_vehicle_permit: "WCTLC For-Hire Vehicle Permit",
    doc_wctlc_insurance: "Proof of Adequate Insurance",
    doc_wctlc_defensive_driving: "Defensive Driving Course Proof of Completion",
    doc_birmingham_operator_permit: "City of Birmingham Operator's Permit",
    doc_huntsville_chauffeur_license: "City of Huntsville Chauffeur License",
    doc_mobile_chauffeur_license: "City of Mobile Chauffeur License",
    doc_montgomery_chauffeur_license: "City of Montgomery Chauffeur License",
    doc_miami_chauffeur_registration: "Miami-Dade Chauffeur Registration",
    doc_orlando_driver_permit: "City of Orlando Driver Permit",
    doc_orlando_insurance: "Certificate of Insurance (City as Additional Insured)",
    doc_tallahassee_driver_permit: "City of Tallahassee Driver Permit",
    doc_tampa_pvdl: "Public Vehicle Driver License (Hillsborough County)",
    doc_tampa_transcript: "Seven-Year Driver License Transcript",
    doc_baton_rouge_chauffeur_license: "City of Baton Rouge Chauffeur License",
    doc_baton_rouge_driving_record: "Official Driving Record",
    doc_baton_rouge_clearance: "Clearance Certificate",
    doc_new_orleans_driver_permit: "CPNC Driver Permit (New Orleans)",
    doc_new_orleans_mvr: "Certified MVR (Within 30 Days)",
    doc_mvfha_driver_permit: "MVFHA Driver Permit",
    doc_charlotte_pvh_permit: "PVH Driver Permit (Charlotte)",
    doc_charlotte_driving_record: "Driving Record",
    doc_durham_pvfh_permit: "PVFH Driver Permit (Durham)",
    doc_charleston_chauffeur_license: "Chauffeur License (Charleston)",
    doc_charleston_driving_record: "Certified 10-Year Driving Record",
    doc_nashville_opvh_permit: "MTLC OPVH Driver Permit",
    doc_nashville_mvr: "Motor Vehicle Record (Within 30 Days)",
    doc_chicago_chauffeur_license: "Restricted Livery Public Chauffeur License (Chicago)",
    doc_chicago_livery_vehicle_license: "Livery Vehicle License (Chicago)",
    doc_chicago_insurance_certificate: "Commercial Insurance Certificate (Chicago)",
    doc_rockford_taxi_driver_license: "Taxi Cab Driver License (Rockford)",
    doc_springfield_il_taxi_driver_license: "Taxicab Driver License (Springfield, IL)",
    doc_evansville_taxi_driver_license: "City of Evansville Taxicab Driver License",
    doc_indianapolis_operator_license: "Operator License (Indianapolis)",
    doc_indianapolis_training_certificate: "Taxi Training Course Certificate (Indianapolis)",
    doc_indianapolis_bmv_record: "Certified BMV Driving Record (Within 10 Days)",
    doc_minneapolis_taxi_driver_license: "Taxi Driver License (Minneapolis)",
    doc_minneapolis_training_certificate: "Taxi Driver Training Certificate (Minneapolis)",
    doc_rochester_mn_taxi_driver_license: "Taxicab Driver License (Rochester, MN)",
    doc_saint_paul_taxi_driver_license: "Taxicab Driver License (Saint Paul)",
    doc_saint_paul_training_proof: "Taxicab Driver Training Course Completion Proof",
    doc_columbia_chauffeur_license: "Chauffeur License (Columbia)",
    doc_independence_vehicle_driver_permit: "Vehicle Driver Permit (Independence)",
    doc_jefferson_city_taxi_driver_permit: "Taxi Driver Permit (Jefferson City)",
    doc_jefferson_city_driving_record: "Certified Driving Record (Missouri DOR)",
    doc_kansas_city_driver_certificate: "Vehicle-for-Hire Driver Certificate (Kansas City)",
    doc_kansas_city_operating_record: "State Operating Record (Missouri)",
    doc_saint_louis_mtc_license: "MTC Driver License (Saint Louis)",
    doc_saint_louis_driver_history: "Missouri Driver History Report (Within 10 Days)",
    doc_lincoln_taxi_driver_license: "Taxicab Driver License (Lincoln)",
    doc_kenosha_taxi_driver_license: "Taxi Driver License (Kenosha)",
    doc_madison_ppv_permit: "Public Passenger Vehicle Driver Permit (Madison)",
    doc_milwaukee_ppv_license: "Public Passenger Vehicle Driver License (Milwaukee)",
    doc_columbus_vfh_license: "Vehicle for Hire Driver License (Columbus)",
    doc_columbus_bmv_abstract: "Certified Ohio BMV Driver Abstract (Within 30 Days)",
    doc_portland_me_livery_license: "Portland Livery Driver License",
    doc_south_portland_taxi_driver_license: "South Portland Taxicab Driver License",
    doc_lowell_hackney_license: "Hackney License (Lowell)",
    doc_springfield_ma_chauffeur_license: "Chauffeur License (Springfield, MA)",
    doc_worcester_taxi_livery_license: "Taxi-Livery Driver License (Worcester)",
    doc_jersey_city_limo_driver_license: "Jersey City Limousine Driver License",
    doc_philadelphia_limo_certificate: "PPA Limousine Driver Certificate",
    doc_little_rock_gt_driver_permit: "Ground Transportation Service Driver Permit (Little Rock)",
    doc_springdale_taxi_driver_permit: "Taxicab Driver Permit (Springdale)",
    doc_boise_cts_driver_license: "Commercial Transportation Service Driver License (Boise)",
    doc_idaho_falls_operator_license: "Public Transportation Operator License (Idaho Falls)",
    doc_okc_vfh_driver_permit: "Vehicle-for-Hire Driver Permit (Oklahoma City)",
    doc_tulsa_chauffeur_license: "City of Tulsa Chauffeur License",
    doc_tulsa_mvr: "MVR Report (Within 30 Days)",
    doc_austin_chauffeur_permit: "Chauffeur Permit (Austin)",
    doc_houston_vfh_driver_license: "City-Issued Vehicle-for-Hire Driver License (Houston)",
    doc_san_antonio_driver_permit: "City of San Antonio Driver Permit (Vehicles for Hire)",
    doc_st_george_for_hire_permit: "For-Hire Driver Permit (St. George)",
    doc_cheyenne_pt_driver_permit: "Public Transportation Driver Permit (Cheyenne)",
    doc_gillette_pt_driver_permit: "Public Transportation Driver Permit (Gillette)",
    doc_clark_county_business_license: "Clark County Business License",
    doc_portland_or_certification: "Executive Town Car Driver Certification (Portland)",
    doc_portland_or_business_license: "City of Portland Business License"
  };
  /* Document types as the API keys them in `docs` (status strings),
     in display order: the New York list first, then the items only
     other states require. The Documents tab renders only the types
     present in the driver's own `docs`, so every driver sees exactly
     his state's list, in this order. */
  var DOC_TYPE_LABELS = {
    profile_picture: "Profile Picture",
    dmv_license: "DMV driving license",
    tlc_license: "TLC License",
    fh1_insurance: "FH-1 Insurance Card",
    registration: "Commercial Vehicle Registration",
    inspection: "NYS DMV Inspection",
    vehicle_permit: "TLC-for-hire Vehicle Permit",
    nj_qualification: "MVC Letter of Qualification",
    nj_municipal_license: "Municipal License to Operate",
    nj_limo_registration: "Limousine Vehicle Registration",
    nj_insurance: "Insurance Certificate",
    vehicle_registration: "Vehicle Registration",
    insurance_card: "Insurance Card",
    al_certificate: "Certificate of Intrastate Authority (APSC)",
    al_form_e: "Form E (Insurance Filing)",
    ca_tcp_permit: "Charter-Party Carrier (TCP) Certificate/Permit (Class A, B or P)",
    ca_driver_statement: "Driver Statement of Application (Form PL739-A)",
    ca_commercial_registration: "Commercial Vehicle Registration (Form PL664)",
    ca_inspection_declaration: "Vehicle Inspection Declaration (Form PL668)",
    co_ll_permit: "Luxury Limousine (LL) Permit",
    co_inspection: "Vehicle Inspection",
    co_form_e: "Form E (Insurance Filing)",
    ct_livery_permit: "Livery Permit (CT DOT)",
    de_certificate: "Certificate of Public Convenience and Necessity",
    de_limo_registration: "Limousine Registration",
    de_inspection: "Vehicle Inspection",
    dc_drivers_record: "Driver's Record",
    dc_ssc: "Social Security Card",
    dc_residency: "Proof of Residency",
    dc_medical_form: "Medical History / Physical Examination Form",
    dc_face_id: "For-Hire Operators (Face ID) License",
    dc_public_vehicle_license: "Public Vehicle-for-Hire License",
    dc_inspection: "DMV Inspection",
    ga_carrier_certificate: "Limousine Carrier Certificate (Georgia DPS)",
    ga_insurance_certificate: "Certificate of Insurance",
    hi_carrier_certificate: "Motor Carrier Certificate / Permit (Form 92-001)",
    hi_vehicle_inventory: "Vehicle Inventory List (Exhibit B)",
    hi_tax_clearance: "Tax Clearance Certificate",
    ks_certificate: "Certificate of Convenience and Necessity (KCC)",
    ky_limousine_certificate: "Limousine Certificate",
    ky_vehicle_license: "Motor Carrier Vehicle License",
    ky_inspection: "Vehicle Inspection",
    me_registration: "Vehicle Registration with HIRE Plates (Class TX)",
    me_jb_filing: "Insurance Certificate for For-Hire Passenger Vehicle (JB Filing)",
    md_for_hire_license: "Passenger-for-Hire Driver's License (PSC)",
    md_inspection_certificate: "Vehicle Inspection Certificate",
    mi_carrier_license: "Limousine Carrier License",
    mn_permit: "Limousine Service Permit (MnDOT)",
    mn_inspection: "Vehicle Inspection",
    mn_form_e: "Form E (Insurance Filing)",
    mo_authority: "Motor Carrier Operating Authority (MoDOT)",
    ne_medical_certificate: "Medical Certificate",
    ne_carrier_authority: "Common / Contract Carrier Authority (PSC)",
    nv_drivers_permit: "Driver's Permit (NTA)",
    nv_cpcn: "Certificate of Public Convenience and Necessity (CPCN)",
    nm_inspection: "Vehicle Inspection",
    oh_livery_registration: "Vehicle Registration (Livery Plates)",
    pa_driving_history: "Driving History (3-Year Record)",
    pa_criminal_history: "Criminal History Record",
    pa_certificate: "Certificate of Public Convenience (PUC)",
    pa_inspection: "Vehicle Inspection",
    pa_form_e: "Form E (Insurance Filing)",
    ri_operator_license: "Taxi-LPMV-PMV Operator's License",
    ri_driving_record: "Driving Record",
    ri_criminal_record: "Record of Criminal Convictions",
    sc_driving_record: "Certified Driving Record (3 Years)",
    sc_charter_certificate: "Class C Charter Certificate",
    sc_ls_registration: "Vehicle Registration (LS Plates)",
    sc_form_e: "Form E (Insurance Filing)",
    tn_citizenship_proof: "Proof of Citizenship or Lawful Permanent Residency",
    tn_residency_proof: "Proof of Tennessee Residency",
    va_authority: "For-Hire Intrastate Operating Authority",
    va_title: "Vehicle Title (Virginia)",
    va_for_hire_registration: "For-Hire Vehicle Registration",
    va_authority_registration: "Operating Authority Registration",
    wa_medical_certificate: "Medical Examiner's Certificate",
    wa_driving_record: "Driving Record",
    wa_carrier_license: "Limousine Carrier License",
    wa_vehicle_certificate: "Limousine Vehicle Certificate",
    wa_chauffeur_addendum: "Limousine Carrier Chauffeur Addendum",
    wa_fh_registration: "Vehicle Registration Certificate (Use Class F/H)",
    wa_inspection_report: "Vehicle Inspection Report",
    wa_insurance_certificate: "Certificate of Insurance",
    dallas_commercial_insurance: "Commercial Insurance Certificate",
    dallas_driver_permit: "Dallas Driver Permit",
    dallas_limo_permit: "City Limo Permit (Dallas / Fort Worth)",
    buffalo_taxi_driver_license: "City of Buffalo Taxi Driver License",
    buffalo_insurance_certificate: "Certificate of Automobile Liability Insurance",
    buffalo_inspection_report: "Vehicle Inspection Report",
    rochester_taxi_driver_license: "City of Rochester Taxicab Driver License",
    rochester_hack_certificate: "Taxicab License Certificate (Hack Plate Certificate)",
    rochester_insurance: "Proof of Insurance",
    syracuse_hack_license: "Taxi (Hack) License",
    syracuse_ground_transportation: "Ground Transportation License",
    syracuse_for_hire_insurance: "Proof of For-Hire Insurance",
    wctlc_driver_permit: "WCTLC For-Hire Driver Permit",
    wctlc_vehicle_permit: "WCTLC For-Hire Vehicle Permit",
    wctlc_insurance: "Proof of Adequate Insurance",
    wctlc_defensive_driving: "Defensive Driving Course Proof of Completion",
    birmingham_operator_permit: "City of Birmingham Operator's Permit",
    huntsville_chauffeur_license: "City of Huntsville Chauffeur License",
    mobile_chauffeur_license: "City of Mobile Chauffeur License",
    montgomery_chauffeur_license: "City of Montgomery Chauffeur License",
    miami_chauffeur_registration: "Miami-Dade Chauffeur Registration",
    orlando_driver_permit: "City of Orlando Driver Permit",
    orlando_insurance: "Certificate of Insurance (City as Additional Insured)",
    tallahassee_driver_permit: "City of Tallahassee Driver Permit",
    tampa_pvdl: "Public Vehicle Driver License (Hillsborough County)",
    tampa_transcript: "Seven-Year Driver License Transcript",
    baton_rouge_chauffeur_license: "City of Baton Rouge Chauffeur License",
    baton_rouge_driving_record: "Official Driving Record",
    baton_rouge_clearance: "Clearance Certificate",
    new_orleans_driver_permit: "CPNC Driver Permit (New Orleans)",
    new_orleans_mvr: "Certified MVR (Within 30 Days)",
    mvfha_driver_permit: "MVFHA Driver Permit",
    charlotte_pvh_permit: "PVH Driver Permit (Charlotte)",
    charlotte_driving_record: "Driving Record",
    durham_pvfh_permit: "PVFH Driver Permit (Durham)",
    charleston_chauffeur_license: "Chauffeur License (Charleston)",
    charleston_driving_record: "Certified 10-Year Driving Record",
    nashville_opvh_permit: "MTLC OPVH Driver Permit",
    nashville_mvr: "Motor Vehicle Record (Within 30 Days)",
    chicago_chauffeur_license: "Restricted Livery Public Chauffeur License (Chicago)",
    chicago_livery_vehicle_license: "Livery Vehicle License (Chicago)",
    chicago_insurance_certificate: "Commercial Insurance Certificate (Chicago)",
    rockford_taxi_driver_license: "Taxi Cab Driver License (Rockford)",
    springfield_il_taxi_driver_license: "Taxicab Driver License (Springfield, IL)",
    evansville_taxi_driver_license: "City of Evansville Taxicab Driver License",
    indianapolis_operator_license: "Operator License (Indianapolis)",
    indianapolis_training_certificate: "Taxi Training Course Certificate (Indianapolis)",
    indianapolis_bmv_record: "Certified BMV Driving Record (Within 10 Days)",
    minneapolis_taxi_driver_license: "Taxi Driver License (Minneapolis)",
    minneapolis_training_certificate: "Taxi Driver Training Certificate (Minneapolis)",
    rochester_mn_taxi_driver_license: "Taxicab Driver License (Rochester, MN)",
    saint_paul_taxi_driver_license: "Taxicab Driver License (Saint Paul)",
    saint_paul_training_proof: "Taxicab Driver Training Course Completion Proof",
    columbia_chauffeur_license: "Chauffeur License (Columbia)",
    independence_vehicle_driver_permit: "Vehicle Driver Permit (Independence)",
    jefferson_city_taxi_driver_permit: "Taxi Driver Permit (Jefferson City)",
    jefferson_city_driving_record: "Certified Driving Record (Missouri DOR)",
    kansas_city_driver_certificate: "Vehicle-for-Hire Driver Certificate (Kansas City)",
    kansas_city_operating_record: "State Operating Record (Missouri)",
    saint_louis_mtc_license: "MTC Driver License (Saint Louis)",
    saint_louis_driver_history: "Missouri Driver History Report (Within 10 Days)",
    lincoln_taxi_driver_license: "Taxicab Driver License (Lincoln)",
    kenosha_taxi_driver_license: "Taxi Driver License (Kenosha)",
    madison_ppv_permit: "Public Passenger Vehicle Driver Permit (Madison)",
    milwaukee_ppv_license: "Public Passenger Vehicle Driver License (Milwaukee)",
    columbus_vfh_license: "Vehicle for Hire Driver License (Columbus)",
    columbus_bmv_abstract: "Certified Ohio BMV Driver Abstract (Within 30 Days)",
    portland_me_livery_license: "Portland Livery Driver License",
    south_portland_taxi_driver_license: "South Portland Taxicab Driver License",
    lowell_hackney_license: "Hackney License (Lowell)",
    springfield_ma_chauffeur_license: "Chauffeur License (Springfield, MA)",
    worcester_taxi_livery_license: "Taxi-Livery Driver License (Worcester)",
    jersey_city_limo_driver_license: "Jersey City Limousine Driver License",
    philadelphia_limo_certificate: "PPA Limousine Driver Certificate",
    little_rock_gt_driver_permit: "Ground Transportation Service Driver Permit (Little Rock)",
    springdale_taxi_driver_permit: "Taxicab Driver Permit (Springdale)",
    boise_cts_driver_license: "Commercial Transportation Service Driver License (Boise)",
    idaho_falls_operator_license: "Public Transportation Operator License (Idaho Falls)",
    okc_vfh_driver_permit: "Vehicle-for-Hire Driver Permit (Oklahoma City)",
    tulsa_chauffeur_license: "City of Tulsa Chauffeur License",
    tulsa_mvr: "MVR Report (Within 30 Days)",
    austin_chauffeur_permit: "Chauffeur Permit (Austin)",
    houston_vfh_driver_license: "City-Issued Vehicle-for-Hire Driver License (Houston)",
    san_antonio_driver_permit: "City of San Antonio Driver Permit (Vehicles for Hire)",
    st_george_for_hire_permit: "For-Hire Driver Permit (St. George)",
    cheyenne_pt_driver_permit: "Public Transportation Driver Permit (Cheyenne)",
    gillette_pt_driver_permit: "Public Transportation Driver Permit (Gillette)",
    clark_county_business_license: "Clark County Business License",
    portland_or_certification: "Executive Town Car Driver Certification (Portland)",
    portland_or_business_license: "City of Portland Business License"
  };
  var DOC_TYPE_ORDER = [
    "profile_picture", "dmv_license", "tlc_license", "fh1_insurance",
    "registration", "inspection", "vehicle_permit",
    "nj_qualification", "nj_municipal_license", "nj_limo_registration",
    "nj_insurance", "buffalo_taxi_driver_license", "vehicle_registration", "insurance_card",
    "dallas_commercial_insurance", "dallas_driver_permit", "dallas_limo_permit",
    "buffalo_insurance_certificate", "buffalo_inspection_report",
    "rochester_taxi_driver_license", "rochester_hack_certificate", "rochester_insurance",
    "syracuse_hack_license", "syracuse_ground_transportation", "syracuse_for_hire_insurance",
    "wctlc_driver_permit", "wctlc_vehicle_permit", "wctlc_insurance", "wctlc_defensive_driving",
    "birmingham_operator_permit", "huntsville_chauffeur_license", "mobile_chauffeur_license",
    "montgomery_chauffeur_license", "miami_chauffeur_registration", "orlando_driver_permit",
    "orlando_insurance", "tallahassee_driver_permit", "tampa_pvdl",
    "tampa_transcript", "baton_rouge_chauffeur_license", "baton_rouge_driving_record",
    "baton_rouge_clearance", "new_orleans_driver_permit", "new_orleans_mvr",
    "mvfha_driver_permit", "charlotte_pvh_permit", "charlotte_driving_record",
    "durham_pvfh_permit", "charleston_chauffeur_license", "charleston_driving_record",
    "nashville_opvh_permit", "nashville_mvr",
    "chicago_chauffeur_license", "chicago_livery_vehicle_license", "chicago_insurance_certificate",
    "rockford_taxi_driver_license", "springfield_il_taxi_driver_license",
    "evansville_taxi_driver_license", "indianapolis_operator_license",
    "indianapolis_training_certificate", "indianapolis_bmv_record",
    "minneapolis_taxi_driver_license", "minneapolis_training_certificate",
    "rochester_mn_taxi_driver_license", "saint_paul_taxi_driver_license",
    "saint_paul_training_proof", "columbia_chauffeur_license",
    "independence_vehicle_driver_permit", "jefferson_city_taxi_driver_permit",
    "jefferson_city_driving_record", "kansas_city_driver_certificate",
    "kansas_city_operating_record", "saint_louis_mtc_license",
    "saint_louis_driver_history", "lincoln_taxi_driver_license",
    "kenosha_taxi_driver_license",
    "madison_ppv_permit", "milwaukee_ppv_license",
    "columbus_vfh_license", "columbus_bmv_abstract",
    "portland_me_livery_license", "south_portland_taxi_driver_license",
    "lowell_hackney_license", "springfield_ma_chauffeur_license",
    "worcester_taxi_livery_license", "jersey_city_limo_driver_license",
    "philadelphia_limo_certificate",
    "little_rock_gt_driver_permit", "springdale_taxi_driver_permit",
    "boise_cts_driver_license", "idaho_falls_operator_license",
    "okc_vfh_driver_permit", "tulsa_chauffeur_license", "tulsa_mvr",
    "austin_chauffeur_permit", "houston_vfh_driver_license",
    "san_antonio_driver_permit", "st_george_for_hire_permit",
    "cheyenne_pt_driver_permit", "gillette_pt_driver_permit",
    "clark_county_business_license",
    "portland_or_certification", "portland_or_business_license",
    "al_certificate", "al_form_e", "ca_tcp_permit", "ca_driver_statement",
    "ca_commercial_registration", "ca_inspection_declaration", "co_ll_permit", "co_inspection",
    "co_form_e", "ct_livery_permit", "de_certificate", "de_limo_registration",
    "de_inspection", "dc_drivers_record", "dc_ssc", "dc_residency",
    "dc_medical_form", "dc_face_id", "dc_public_vehicle_license", "dc_inspection",
    "ga_carrier_certificate", "ga_insurance_certificate", "hi_carrier_certificate", "hi_vehicle_inventory",
    "hi_tax_clearance", "ks_certificate", "ky_limousine_certificate", "ky_vehicle_license",
    "ky_inspection", "me_registration", "me_jb_filing", "md_for_hire_license",
    "md_inspection_certificate", "mi_carrier_license", "mn_permit", "mn_inspection",
    "mn_form_e", "mo_authority", "ne_medical_certificate", "ne_carrier_authority",
    "nv_drivers_permit", "nv_cpcn", "nm_inspection", "oh_livery_registration",
    "pa_driving_history", "pa_criminal_history", "pa_certificate", "pa_inspection",
    "pa_form_e", "ri_operator_license", "ri_driving_record", "ri_criminal_record",
    "sc_driving_record", "sc_charter_certificate", "sc_ls_registration", "sc_form_e",
    "tn_citizenship_proof", "tn_residency_proof", "va_authority", "va_title",
    "va_for_hire_registration", "va_authority_registration", "wa_medical_certificate", "wa_driving_record",
    "wa_carrier_license", "wa_vehicle_certificate", "wa_chauffeur_addendum", "wa_fh_registration",
    "wa_inspection_report", "wa_insurance_certificate"
  ];
  /* Doc types with a static item in the registration form (the New
     York list). Items for other states are built by JS from the
     states endpoint when their state is chosen. */
  var STATIC_DOC_TYPES = [
    "profile_picture", "dmv_license", "tlc_license", "fh1_insurance",
    "registration", "inspection", "vehicle_permit"
  ];
  /* Doc type -> multipart field name (profile_picture comes from
     profile_photo). Mirrors the server's FIELD_FOR_DOC_TYPE. */
  var FIELD_FOR_DOC_TYPE = {
    profile_picture: "profile_photo",
    dmv_license: "doc_dmv_license",
    tlc_license: "doc_tlc_license",
    fh1_insurance: "doc_fh1",
    registration: "doc_registration",
    inspection: "doc_inspection",
    vehicle_permit: "doc_vehicle_permit",
    nj_qualification: "doc_nj_qualification",
    nj_municipal_license: "doc_nj_municipal_license",
    nj_limo_registration: "doc_nj_limo_registration",
    nj_insurance: "doc_nj_insurance",
    vehicle_registration: "doc_vehicle_registration",
    insurance_card: "doc_insurance_card",
    al_certificate: "doc_al_certificate",
    al_form_e: "doc_al_form_e",
    ca_tcp_permit: "doc_ca_tcp_permit",
    ca_driver_statement: "doc_ca_driver_statement",
    ca_commercial_registration: "doc_ca_commercial_registration",
    ca_inspection_declaration: "doc_ca_inspection_declaration",
    co_ll_permit: "doc_co_ll_permit",
    co_inspection: "doc_co_inspection",
    co_form_e: "doc_co_form_e",
    ct_livery_permit: "doc_ct_livery_permit",
    de_certificate: "doc_de_certificate",
    de_limo_registration: "doc_de_limo_registration",
    de_inspection: "doc_de_inspection",
    dc_drivers_record: "doc_dc_drivers_record",
    dc_ssc: "doc_dc_ssc",
    dc_residency: "doc_dc_residency",
    dc_medical_form: "doc_dc_medical_form",
    dc_face_id: "doc_dc_face_id",
    dc_public_vehicle_license: "doc_dc_public_vehicle_license",
    dc_inspection: "doc_dc_inspection",
    ga_carrier_certificate: "doc_ga_carrier_certificate",
    ga_insurance_certificate: "doc_ga_insurance_certificate",
    hi_carrier_certificate: "doc_hi_carrier_certificate",
    hi_vehicle_inventory: "doc_hi_vehicle_inventory",
    hi_tax_clearance: "doc_hi_tax_clearance",
    ks_certificate: "doc_ks_certificate",
    ky_limousine_certificate: "doc_ky_limousine_certificate",
    ky_vehicle_license: "doc_ky_vehicle_license",
    ky_inspection: "doc_ky_inspection",
    me_registration: "doc_me_registration",
    me_jb_filing: "doc_me_jb_filing",
    md_for_hire_license: "doc_md_for_hire_license",
    md_inspection_certificate: "doc_md_inspection_certificate",
    mi_carrier_license: "doc_mi_carrier_license",
    mn_permit: "doc_mn_permit",
    mn_inspection: "doc_mn_inspection",
    mn_form_e: "doc_mn_form_e",
    mo_authority: "doc_mo_authority",
    ne_medical_certificate: "doc_ne_medical_certificate",
    ne_carrier_authority: "doc_ne_carrier_authority",
    nv_drivers_permit: "doc_nv_drivers_permit",
    nv_cpcn: "doc_nv_cpcn",
    nm_inspection: "doc_nm_inspection",
    oh_livery_registration: "doc_oh_livery_registration",
    pa_driving_history: "doc_pa_driving_history",
    pa_criminal_history: "doc_pa_criminal_history",
    pa_certificate: "doc_pa_certificate",
    pa_inspection: "doc_pa_inspection",
    pa_form_e: "doc_pa_form_e",
    ri_operator_license: "doc_ri_operator_license",
    ri_driving_record: "doc_ri_driving_record",
    ri_criminal_record: "doc_ri_criminal_record",
    sc_driving_record: "doc_sc_driving_record",
    sc_charter_certificate: "doc_sc_charter_certificate",
    sc_ls_registration: "doc_sc_ls_registration",
    sc_form_e: "doc_sc_form_e",
    tn_citizenship_proof: "doc_tn_citizenship_proof",
    tn_residency_proof: "doc_tn_residency_proof",
    va_authority: "doc_va_authority",
    va_title: "doc_va_title",
    va_for_hire_registration: "doc_va_for_hire_registration",
    va_authority_registration: "doc_va_authority_registration",
    wa_medical_certificate: "doc_wa_medical_certificate",
    wa_driving_record: "doc_wa_driving_record",
    wa_carrier_license: "doc_wa_carrier_license",
    wa_vehicle_certificate: "doc_wa_vehicle_certificate",
    wa_chauffeur_addendum: "doc_wa_chauffeur_addendum",
    wa_fh_registration: "doc_wa_fh_registration",
    wa_inspection_report: "doc_wa_inspection_report",
    wa_insurance_certificate: "doc_wa_insurance_certificate",
    dallas_commercial_insurance: "doc_dallas_commercial_insurance",
    dallas_driver_permit: "doc_dallas_driver_permit",
    dallas_limo_permit: "doc_dallas_limo_permit",
    buffalo_taxi_driver_license: "doc_buffalo_taxi_driver_license",
    buffalo_insurance_certificate: "doc_buffalo_insurance_certificate",
    buffalo_inspection_report: "doc_buffalo_inspection_report",
    rochester_taxi_driver_license: "doc_rochester_taxi_driver_license",
    rochester_hack_certificate: "doc_rochester_hack_certificate",
    rochester_insurance: "doc_rochester_insurance",
    syracuse_hack_license: "doc_syracuse_hack_license",
    syracuse_ground_transportation: "doc_syracuse_ground_transportation",
    syracuse_for_hire_insurance: "doc_syracuse_for_hire_insurance",
    wctlc_driver_permit: "doc_wctlc_driver_permit",
    wctlc_vehicle_permit: "doc_wctlc_vehicle_permit",
    wctlc_insurance: "doc_wctlc_insurance",
    wctlc_defensive_driving: "doc_wctlc_defensive_driving",
    birmingham_operator_permit: "doc_birmingham_operator_permit",
    huntsville_chauffeur_license: "doc_huntsville_chauffeur_license",
    mobile_chauffeur_license: "doc_mobile_chauffeur_license",
    montgomery_chauffeur_license: "doc_montgomery_chauffeur_license",
    miami_chauffeur_registration: "doc_miami_chauffeur_registration",
    orlando_driver_permit: "doc_orlando_driver_permit",
    orlando_insurance: "doc_orlando_insurance",
    tallahassee_driver_permit: "doc_tallahassee_driver_permit",
    tampa_pvdl: "doc_tampa_pvdl",
    tampa_transcript: "doc_tampa_transcript",
    baton_rouge_chauffeur_license: "doc_baton_rouge_chauffeur_license",
    baton_rouge_driving_record: "doc_baton_rouge_driving_record",
    baton_rouge_clearance: "doc_baton_rouge_clearance",
    new_orleans_driver_permit: "doc_new_orleans_driver_permit",
    new_orleans_mvr: "doc_new_orleans_mvr",
    mvfha_driver_permit: "doc_mvfha_driver_permit",
    charlotte_pvh_permit: "doc_charlotte_pvh_permit",
    charlotte_driving_record: "doc_charlotte_driving_record",
    durham_pvfh_permit: "doc_durham_pvfh_permit",
    charleston_chauffeur_license: "doc_charleston_chauffeur_license",
    charleston_driving_record: "doc_charleston_driving_record",
    nashville_opvh_permit: "doc_nashville_opvh_permit",
    nashville_mvr: "doc_nashville_mvr",
    chicago_chauffeur_license: "doc_chicago_chauffeur_license",
    chicago_livery_vehicle_license: "doc_chicago_livery_vehicle_license",
    chicago_insurance_certificate: "doc_chicago_insurance_certificate",
    rockford_taxi_driver_license: "doc_rockford_taxi_driver_license",
    springfield_il_taxi_driver_license: "doc_springfield_il_taxi_driver_license",
    evansville_taxi_driver_license: "doc_evansville_taxi_driver_license",
    indianapolis_operator_license: "doc_indianapolis_operator_license",
    indianapolis_training_certificate: "doc_indianapolis_training_certificate",
    indianapolis_bmv_record: "doc_indianapolis_bmv_record",
    minneapolis_taxi_driver_license: "doc_minneapolis_taxi_driver_license",
    minneapolis_training_certificate: "doc_minneapolis_training_certificate",
    rochester_mn_taxi_driver_license: "doc_rochester_mn_taxi_driver_license",
    saint_paul_taxi_driver_license: "doc_saint_paul_taxi_driver_license",
    saint_paul_training_proof: "doc_saint_paul_training_proof",
    columbia_chauffeur_license: "doc_columbia_chauffeur_license",
    independence_vehicle_driver_permit: "doc_independence_vehicle_driver_permit",
    jefferson_city_taxi_driver_permit: "doc_jefferson_city_taxi_driver_permit",
    jefferson_city_driving_record: "doc_jefferson_city_driving_record",
    kansas_city_driver_certificate: "doc_kansas_city_driver_certificate",
    kansas_city_operating_record: "doc_kansas_city_operating_record",
    saint_louis_mtc_license: "doc_saint_louis_mtc_license",
    saint_louis_driver_history: "doc_saint_louis_driver_history",
    lincoln_taxi_driver_license: "doc_lincoln_taxi_driver_license",
    kenosha_taxi_driver_license: "doc_kenosha_taxi_driver_license",
    madison_ppv_permit: "doc_madison_ppv_permit",
    milwaukee_ppv_license: "doc_milwaukee_ppv_license",
    columbus_vfh_license: "doc_columbus_vfh_license",
    columbus_bmv_abstract: "doc_columbus_bmv_abstract",
    portland_me_livery_license: "doc_portland_me_livery_license",
    south_portland_taxi_driver_license: "doc_south_portland_taxi_driver_license",
    lowell_hackney_license: "doc_lowell_hackney_license",
    springfield_ma_chauffeur_license: "doc_springfield_ma_chauffeur_license",
    worcester_taxi_livery_license: "doc_worcester_taxi_livery_license",
    jersey_city_limo_driver_license: "doc_jersey_city_limo_driver_license",
    philadelphia_limo_certificate: "doc_philadelphia_limo_certificate",
    little_rock_gt_driver_permit: "doc_little_rock_gt_driver_permit",
    springdale_taxi_driver_permit: "doc_springdale_taxi_driver_permit",
    boise_cts_driver_license: "doc_boise_cts_driver_license",
    idaho_falls_operator_license: "doc_idaho_falls_operator_license",
    okc_vfh_driver_permit: "doc_okc_vfh_driver_permit",
    tulsa_chauffeur_license: "doc_tulsa_chauffeur_license",
    tulsa_mvr: "doc_tulsa_mvr",
    austin_chauffeur_permit: "doc_austin_chauffeur_permit",
    houston_vfh_driver_license: "doc_houston_vfh_driver_license",
    san_antonio_driver_permit: "doc_san_antonio_driver_permit",
    st_george_for_hire_permit: "doc_st_george_for_hire_permit",
    cheyenne_pt_driver_permit: "doc_cheyenne_pt_driver_permit",
    gillette_pt_driver_permit: "doc_gillette_pt_driver_permit",
    clark_county_business_license: "doc_clark_county_business_license",
    portland_or_certification: "doc_portland_or_certification",
    portland_or_business_license: "doc_portland_or_business_license"
  };
  var STAGES = ["en_route", "arrived", "start", "complete"];
  var STAGE_BUTTON = {
    en_route: "Head to pickup",
    arrived: "I have arrived",
    start: "Start trip",
    complete: "Complete trip"
  };
  /* Customer-facing class names, as the API returns them in
     vehicle_class_label; the map is only a fallback. */
  var CLASS_LABELS = { sedan: "Business Class", suv: "Business SUV" };
  function classLabelFor(obj) {
    if (!obj) return "";
    return obj.vehicle_class_label || CLASS_LABELS[obj.vehicle_class] || "";
  }

  var state = {
    token: null,
    driver: null,
    available: false,
    offersTimer: null,
    noShowTimer: null,
    reminderTimer: null,
    reminderChimedBookingId: null,
    trip: null,
    stageIndex: 0,
    watchId: null,
    lastPosition: null,
    locationError: false,
    advancing: false,
    seenOfferIds: {},
    toneTimer: null,
    toneStopAt: 0,
    toneOfferIds: {},
    lastOffersSig: "",
    chatTimer: null,
    lastChatSig: "",
    chatLanguage: "en",
    audioCtx: null,
    /* Referrer code captured from a /driver?ref=CODE referral link,
       sent with the registration submit and then cleared. Kept in
       memory only — never stored — so it cannot leak into a later
       session on a shared device. */
    pendingReferralCode: null,
    /* Stripe payout setup (GET /api/drivers/me/payout-setup) and the
       unpaid-earnings total available for instant cash-out (summed
       from the unpaid pay weeks — the driver's own earnings only). */
    payoutSetup: null,
    unpaidCashout: null,
    payoutFeeRate: 0.015
  };

  function $(id) { return document.getElementById(id); }
  function show(el) { el.classList.remove("hidden"); }
  function hide(el) { el.classList.add("hidden"); }
  function money(n) {
    if (n === null || n === undefined || isNaN(Number(n))) return "—";
    return "$" + Number(n).toFixed(2);
  }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function getToken() {
    try { return window.localStorage.getItem(TOKEN_KEY); } catch (e) { return state.token; }
  }
  function saveToken(t) {
    state.token = t;
    try { window.localStorage.setItem(TOKEN_KEY, t); } catch (e) { /* private mode */ }
  }
  function clearToken() {
    state.token = null;
    try { window.localStorage.removeItem(TOKEN_KEY); } catch (e) { /* private mode */ }
  }
  function authHeaders(extra) {
    var h = { "X-Driver-Token": state.token || "" };
    if (extra) { for (var k in extra) h[k] = extra[k]; }
    return h;
  }
  function unwrapDriver(j) {
    if (!j) return null;
    return j.driver || j;
  }
  function pickNumber(obj, keys) {
    for (var i = 0; i < keys.length; i++) {
      var v = obj ? obj[keys[i]] : undefined;
      if (v !== null && v !== undefined && !isNaN(Number(v))) return Number(v);
    }
    return null;
  }
  function maskBank(value) {
    var digits = String(value || "").replace(/\D/g, "");
    if (!digits) return "Saved";
    if (digits.length <= 4) return "••••" + digits;
    return "••••" + digits.slice(-4);
  }

  /* ---------- Screens ---------- */
  var SCREENS = ["login", "register", "home", "trip", "earnings", "tax", "documents", "profile"];
  function showScreen(name) {
    SCREENS.forEach(function (s) {
      var el = $("screen-" + s);
      if (el) { if (s === name) show(el); else hide(el); }
    });
    /* Home menu (top-left) closes on every screen change, and the
       Home button shows only on the signed-in screens that show the
       tab bar (home, earnings, tax, documents, profile). */
    hide($("home-menu"));
    if (name === "login" || name === "register" || name === "trip") {
      hide($("tabbar"));
      hide($("home-menu-btn"));
    } else {
      show($("tabbar"));
      show($("home-menu-btn"));
      document.querySelectorAll("#tabbar button").forEach(function (b) {
        b.classList.toggle("active", b.getAttribute("data-screen") === name);
      });
    }
    /* Owner decision 2026-11-20 ~06:45 EST: the "Drive with Noel
       Chauffer" marketing section (Why drive / How to start / FAQs)
       is recruitment content for SIGNED-OUT visitors only. A
       signed-in driver opening the app must see none of it — only
       his jobs. So it shows on the login/register screens and is
       hidden on every signed-in screen (home, trip, earnings, tax,
       documents, profile). The section stays in the page HTML (and
       its FAQ schema) so Google still indexes the driver page. */
    var seo = document.querySelector(".seo-drive");
    if (seo) { if (name === "login" || name === "register") show(seo); else hide(seo); }
    window.scrollTo(0, 0);
    if (name === "home") { refreshOffers(); }
    if (name === "earnings") { loadEarnings(); loadPayoutSetup(); }
    if (name === "tax") { loadTaxInfo(); }
    if (name === "documents") { renderDocuments(); }
    if (name === "profile") { renderProfile(); loadDriverReferral(); }
  }
  document.querySelectorAll("#tabbar button").forEach(function (b) {
    b.addEventListener("click", function () { showScreen(b.getAttribute("data-screen")); });
  });

  /* ---------- Home menu (top-left) ---------- */
  /* Owner decision 2026-11-21 ~23:24 EST: a "Home" button at the
     top left of the signed-in driver screens. Tapping it shows a
     menu with Earnings, Tax info, Documents and Profile, each
     opening its existing screen — like Uber Driver's upper-left
     menu (owner 2026-11-21 ~23:26 EST, "jaisa Uber Driver ka hai"),
     with Noel's sections and the "Home" label he ordered. The
     bottom tab bar stays as it is. */
  $("home-menu-btn").addEventListener("click", function () {
    $("home-menu").classList.toggle("hidden");
  });
  document.querySelectorAll("#home-menu button").forEach(function (b) {
    b.addEventListener("click", function () { showScreen(b.getAttribute("data-screen")); });
  });

  /* ---------- Boot: signed-out drivers land on sign-in, signed-in drivers go straight to jobs ---------- */
  /* Owner decision 2026-11-18: the driver app opens on a login
     screen (email + password only) when signed out, with new
     registration behind a link at the bottom. A signed-in driver
     never sees the registration form again. */
  /* Driver referral link (owner decision 2026-11-18): a friend who
     clicks a driver's /driver?ref=CODE link lands straight in
     driver registration — no sign-in screen first — and the
     referrer is captured for the registration submit. Only for
     signed-out devices: a signed-in driver goes to his jobs as
     usual, and the password-reset link still wins. The query is
     stripped from the address bar at once, so a later reload —
     including after Log out — lands on sign-in as usual. A reload
     in the middle of registration loses the referrer; the friend
     re-clicks the link to restore it. */
  function referralCodeFromUrl() {
    try {
      var ref = new URLSearchParams(window.location.search).get("ref");
      return (ref || "").trim() || null;
    } catch (e) { return null; }
  }
  function stripReferralFromUrl() {
    try {
      window.history.replaceState(null, "", window.location.pathname);
    } catch (e) { /* old browser: the query stays, harmless */ }
  }
  function boot() {
    /* Password reset: a /driver?reset=<token> link opens the
       set-new-password form instead of the normal view, even on a
       device with a saved sign-in (the reset rotates the token, so
       the old session stops working anyway). */
    var resetToken = null;
    try { resetToken = new URLSearchParams(window.location.search).get("reset"); } catch (e) { /* old browser */ }
    if (resetToken) { showResetForm(resetToken); return; }
    var token = getToken();
    if (!token) {
      var referralCode = referralCodeFromUrl();
      if (referralCode) {
        state.pendingReferralCode = referralCode;
        stripReferralFromUrl();
        showScreen("register");
        return;
      }
      showScreen("login");
      return;
    }
    state.token = token;
    fetch("/api/drivers/me", { headers: authHeaders() })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !unwrapDriver(res.j)) {
          clearToken();
          showScreen("login");
          return;
        }
        enterApp(unwrapDriver(res.j));
      })
      .catch(function () {
        /* Offline: fall back to sign-in rather than a dead screen. */
        showScreen("login");
      });
  }

  function enterApp(driver) {
    state.driver = driver || {};
    state.available = !!state.driver.available;
    initChatLanguage(state.driver);
    renderHello();
    renderAvailability();
    /* Load the alerted-offer set before the first poll, so a refresh
       never re-rings an old offer and a new offer rings at once. */
    loadSeenOfferIds();
    showScreen("home");
    startOffersPolling();
    restoreActiveTrip();
  }

  /* If the driver already has an assigned trip (e.g. after a reload),
     restore the trip screen at the right stage instead of losing it. */
  function tripFromBooking(b, fallbackId) {
    return {
      id: b.booking_id || b.id || fallbackId,
      pickup: b.pickup,
      dropoff: b.dropoff,
      pickup_lat: pickNumber(b, ["pickup_lat"]),
      pickup_lng: pickNumber(b, ["pickup_lng"]),
      dropoff_lat: pickNumber(b, ["dropoff_lat"]),
      dropoff_lng: pickNumber(b, ["dropoff_lng"]),
      date: b.date,
      time: b.time,
      ride_type: b.ride_type,
      hours: b.hours,
      vehicle_class: b.vehicle_class,
      vehicle_class_label: b.vehicle_class_label,
      route_url: b.route_url,
      route_waze_url: b.route_waze_url,
      free_waiting_minutes: b.free_waiting_minutes,
      airport_pickup: b.airport_pickup,
      customer_name: b.customer_name,
      customer_phone: b.customer_phone,
      flight_number: b.flight_number || null,
      airline_name: b.airline_name || null,
      terminal: b.terminal || null
    };
  }
  function restoreActiveTrip() {
    fetch("/api/drivers/me/active-trip", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var b = j && j.booking;
        if (!b || !b.id) return;
        state.trip = tripFromBooking(b);
        var stageByStatus = { accepted: 0, en_route: 1, arrived: 2, in_progress: 3 };
        state.stageIndex = stageByStatus[b.status] !== undefined ? stageByStatus[b.status] : 0;
        renderTrip();
        showScreen("trip");
        if (b.status === "en_route" || b.status === "arrived" || b.status === "in_progress") {
          startLocationSharing();
        }
      })
      .catch(function () { /* no active trip, or unreachable: stay on Home */ });
  }

  function renderHello() {
    var line = $("hello-line");
    if (state.driver && state.driver.name) {
      line.textContent = "Hello, " + state.driver.name;
      show(line);
    } else {
      hide(line);
    }
  }

  /* ---------- File previews (photo check before saving) ---------- */
  /* Bound once per file input, including document items built later
     for other states: the preview shows the chosen photo (passport
     frame for the profile picture) with a remove option, so the
     driver checks each photo before saving. */
  function bindFilePreview(field) {
    var input = $("file-" + field);
    if (!input) return;
    input.addEventListener("change", function () {
      /* Picking a new file clears this item's red error state right
         away (owner decision 2026-11-18: the failing item turns
         red, and a fresh pick starts it clean). */
      clearDocItemError(field);
      var box = $("preview-" + field);
      box.innerHTML = "";
      box.classList.remove("passport-preview");
      var file = input.files && input.files[0];
      if (!file) return;
      /* Profile photo: run the passport-style check right away, so
         a sideways or tiny photo turns its own item red as soon as
         it is picked, not only at submit. The callback only marks
         when this file is still the chosen one, so a newer pick is
         never blamed for an older photo. */
      if (field === "profile_photo") {
        checkProfilePhoto(file, function (photoError) {
          if (photoError && input.files && input.files[0] === file) {
            markDocItemError(field, photoError);
          }
        });
      }
      var isImage = file.type && file.type.indexOf("image/") === 0;
      if (isImage) {
        var img = document.createElement("img");
        img.alt = "Preview — check it is clear and complete, retake if blurry";
        img.src = URL.createObjectURL(file);
        /* Profile picture shows passport-style: a cropped face frame,
           not the whole photo. */
        if (field === "profile_photo") box.classList.add("passport-preview");
        box.appendChild(img);
      } else {
        var p = document.createElement("p");
        p.className = "file-name";
        p.textContent = "Selected file: " + file.name + " — please check it is the right document.";
        box.appendChild(p);
      }
      var rm = document.createElement("button");
      rm.type = "button";
      rm.className = "preview-remove";
      rm.textContent = isImage ? "Remove photo" : "Remove file";
      rm.addEventListener("click", function () {
        input.value = "";
        box.innerHTML = "";
        box.classList.remove("passport-preview");
        clearDocItemError(field);
      });
      box.appendChild(rm);
    });
  }
  FILE_FIELDS.forEach(bindFilePreview);

  /* ---------- Registration ---------- */
  /* Passport-style profile-photo pre-check (owner decision
     2026-11-17): portrait orientation and a minimum size, so a
     sideways or tiny photo is refused with a clear message before
     anything is submitted. The server enforces the same rules; an
     unreadable file here is left for the server to judge. */
  function checkProfilePhoto(file, done) {
    if (!file) { done(null); return; }
    var url = URL.createObjectURL(file);
    var img = new Image();
    img.onload = function () {
      URL.revokeObjectURL(url);
      var w = img.naturalWidth, h = img.naturalHeight;
      if (h <= w) {
        done("Profile photo must be a portrait photo (taller than it is wide) — please upload a passport-style photo of your face.");
        return;
      }
      if (w < 300) {
        done("Profile photo is too small — please upload a larger, clear photo of your face (at least 300 pixels wide).");
        return;
      }
      done(null);
    };
    img.onerror = function () { URL.revokeObjectURL(url); done(null); };
    img.src = url;
  }

  /* Plate format check (owner decision 2026-11-17, "Format check
     laga do"): Uber-style generic US plate rule — spaces and dashes
     ignored, 2-8 letters or digits, stored uppercase. The server
     enforces the same rule with the same wording. */
  function normalizePlate(value) {
    return (value || "").replace(/[\s\-]/g, "").toUpperCase();
  }
  function plateError(value) {
    if (!/^[A-Z0-9]{2,8}$/.test(normalizePlate(value))) {
      return "Please enter a valid plate number (letters and numbers only).";
    }
    return null;
  }

  /* Keep the plate field uppercase as the driver types, Uber-style;
     spaces and dashes are stripped when the form is submitted. */
  $("reg-plate").addEventListener("input", function () {
    var field = $("reg-plate");
    var upper = field.value.toUpperCase();
    if (field.value !== upper) field.value = upper;
  });

  /* ---------- Per-item red error state (registration) ---------- */
  /* Owner decision 2026-11-18 (voice call): "driver ka koi cheez
     fail ho rahi upload kare baad to uska error pe maloom ho jana
     ... wo side wala red mein kar dena" — when a document upload
     fails, the driver must be able to tell WHICH item failed, so
     the failing item itself turns red and shows the message inside
     it. Until now every registration error went into one shared
     box, which never said which document failed. The shared box
     keeps working exactly as before; this is purely additive
     visual feedback, and no validation rule changes. */
  function markDocItemError(field, message) {
    var item = $("doc-item-" + field);
    if (!item) return;
    item.classList.add("has-error");
    var el = $("doc-error-" + field);
    if (el) el.textContent = message;
  }
  function clearDocItemError(field) {
    var item = $("doc-item-" + field);
    if (item) item.classList.remove("has-error");
    var el = $("doc-error-" + field);
    if (el) el.textContent = "";
  }
  /* Every marked item, including city-specific items built later:
     FILE_FIELDS covers only the static list, so this walks the DOM
     instead of a field list. */
  function clearAllDocItemErrors() {
    var marked = document.querySelectorAll(".doc-item.has-error");
    for (var i = 0; i < marked.length; i++) {
      marked[i].classList.remove("has-error");
      var el = marked[i].querySelector(".doc-error");
      if (el) el.textContent = "";
    }
  }
  /* The missing-document wording for one item: the same sentence
     the shared box uses, naming just this item. */
  function missingDocMessage(field) {
    return "Missing document: " + DOC_LABELS[field] +
      ". Please upload all required documents to complete registration.";
  }
  /* Parse the label list out of a server "Missing document: A, B,
     ..." error into field names. Labels are matched against the
     known DOC_LABELS values, longest first, because some labels
     contain ", " themselves ("Class A, B or P", "Springfield,
     IL"), so splitting on ", " would break them. A label shared by
     several fields (same wording in different states) resolves to
     the field in the current required list. Unknown text stops the
     parse — it never invents a field. */
  function parseMissingDocFields(listText, requiredFields) {
    var suffix = ". Please upload all required documents to complete registration.";
    var rest = listText;
    var cut = rest.indexOf(suffix);
    if (cut !== -1) rest = rest.slice(0, cut);
    else if (rest.slice(-1) === ".") rest = rest.slice(0, -1);
    var requiredSet = {};
    (requiredFields || []).forEach(function (f) { requiredSet[f] = true; });
    var candidates = Object.keys(DOC_LABELS).map(function (field) {
      return { label: DOC_LABELS[field], field: field, preferred: !!requiredSet[field] };
    });
    candidates.sort(function (a, b) {
      if (b.label.length !== a.label.length) return b.label.length - a.label.length;
      return (b.preferred ? 1 : 0) - (a.preferred ? 1 : 0);
    });
    var fields = [];
    while (rest.length) {
      var matched = null;
      for (var i = 0; i < candidates.length; i++) {
        var cand = candidates[i];
        if (rest.indexOf(cand.label) === 0 &&
            (rest.length === cand.label.length ||
             rest.slice(cand.label.length, cand.label.length + 2) === ", ")) {
          matched = cand;
          break;
        }
      }
      if (!matched) break;
      if (fields.indexOf(matched.field) === -1) fields.push(matched.field);
      rest = rest.slice(matched.label.length);
      if (rest.indexOf(", ") === 0) rest = rest.slice(2);
      else if (rest.length) break;
    }
    return fields;
  }
  /* Map a registration server error to the document item(s) it is
     about, and mark them red. Only document errors map: "Missing
     document: ..." (labels), "Profile photo ..." (the profile
     photo), and the upload checks, which start with the multipart
     field name ("<field> must be one of: ...", "<field> exceeds
     the 5MB limit.", "<field> is empty."). Anything else — plate,
     password, network, generic — maps to nothing, so no document
     is ever marked red for a non-document error. */
  function markDocErrorsFromServer(message, requiredFields) {
    if (!message) return;
    var missingPrefix = "Missing document: ";
    if (message.indexOf(missingPrefix) === 0) {
      parseMissingDocFields(message.slice(missingPrefix.length), requiredFields)
        .forEach(function (field) { markDocItemError(field, missingDocMessage(field)); });
      return;
    }
    if (message.indexOf("Profile photo") === 0) {
      markDocItemError("profile_photo", message);
      return;
    }
    var fields = Object.keys(DOC_LABELS);
    for (var i = 0; i < fields.length; i++) {
      if (message.indexOf(fields[i] + " ") === 0) {
        markDocItemError(fields[i], message);
        return;
      }
    }
    /* Expiry and photo-sanity errors name the document by its label
       ("Your DMV driving license is expired …", "Please enter the
       expiry date for your TLC License."), so map the label to its
       item. Longest labels first, so "Commercial Vehicle
       Registration" wins over "Vehicle Registration" inside it. */
    var labelled = Object.keys(DOC_LABELS).map(function (f) {
      return { field: f, label: DOC_LABELS[f] };
    });
    labelled.sort(function (a, b) { return b.label.length - a.label.length; });
    for (var j = 0; j < labelled.length; j++) {
      if (message.indexOf(labelled[j].label) !== -1) {
        markDocItemError(labelled[j].field, message);
        return;
      }
    }
  }

  $("register-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("register-error");
    err.textContent = "";
    /* A fresh submit attempt clears every per-item red state first;
       the checks below re-mark whatever still fails. */
    clearAllDocItemErrors();
    var name = $("reg-name").value.trim();
    var phone = $("reg-phone").value.trim();
    var email = $("reg-email").value.trim();
    var password = $("reg-password").value;
    var passwordConfirm = $("reg-password-confirm").value;
    var stateName = $("reg-state").value.trim();
    var cityName = $("reg-city").value.trim();
    var carModel = $("reg-car-model").value.trim();
    var carYear = $("reg-car-year").value.trim();
    var carColour = $("reg-car-colour").value.trim();
    var plate = $("reg-plate").value.trim();
    var acct = $("reg-bank-account").value.trim();
    var routing = $("reg-bank-routing").value.trim();
    if (!name || !phone || !email || !password || !passwordConfirm || !stateName || !cityName || !carModel || !carYear || !carColour || !plate || !acct || !routing) {
      err.textContent = "Please fill in every field, including your bank details.";
      return;
    }
    /* Password for email+password sign-in: at least 6 characters and
       matching confirmation. The server enforces the same rules and
       stores only a hash, never the password itself. */
    if (password.length < 6) {
      err.textContent = "Password must be at least 6 characters.";
      return;
    }
    if (password !== passwordConfirm) {
      err.textContent = "Passwords do not match.";
      return;
    }
    if (carListLoaded && carModels.indexOf(carModel) === -1) {
      err.textContent = "Please choose your car model from the list.";
      return;
    }
    if (stateListLoaded && stateNames.indexOf(stateName) === -1) {
      err.textContent = "Please choose your state from the list.";
      return;
    }
    if (cityListLoaded && citiesForState(stateName).indexOf(cityName) === -1) {
      err.textContent = "Please choose your city from the list.";
      return;
    }
    /* Plate format: Uber-style generic US rule (see plateError
       above). The normalized value is what gets submitted, so the
       stored plate is always uppercase with no spaces or dashes. */
    var plateProblem = plateError(plate);
    if (plateProblem) {
      err.textContent = plateProblem;
      return;
    }
    plate = normalizePlate(plate);
    /* Bank details are COMPULSORY for payout setup (owner decision
       2026-11-20): routing number must be 9 digits with a valid ABA
       checksum, account number 4-17 digits. The server enforces the
       same rules; this pre-check gives the fast, clear message. */
    if (!/^\d{9}$/.test(routing) ||
        [3, 7, 1, 3, 7, 1, 3, 7, 1].reduce(function (sum, w, i) {
          return sum + w * parseInt(routing[i], 10);
        }, 0) % 10 !== 0) {
      err.textContent = "Routing number is not valid. Please check it and try again.";
      return;
    }
    if (!/^\d{4,17}$/.test(acct)) {
      err.textContent = "Bank account number must be 4 to 17 digits.";
      return;
    }
    /* Which documents are compulsory depends on the state and the
       city (New York keeps its 7; other states have their own list
       or the generic base list; a city with a verified
       city-specific list, Dallas today, overrides its state list).
       Without a state the list is unknown, so the form cannot
       submit yet. */
    var requiredFields = requiredFileFields(stateName, cityName);
    if (!requiredFields.length) {
      err.textContent = "Please choose your state from the list.";
      return;
    }
    /* Owner decision 2026-11-17: documents are compulsory — the form
       must not submit until every item is uploaded. The message names
       each missing item, in the owner's words ("Missing document").
       Nothing is cleared: uploads already chosen stay in the form, so
       the driver only adds what is missing and submits again. */
    var missingDocs = [];
    var missingFields = [];
    requiredFields.forEach(function (field) {
      var input = $("file-" + field);
      if (!input || !input.files || !input.files[0]) {
        missingDocs.push(DOC_LABELS[field]);
        missingFields.push(field);
      }
    });
    if (missingDocs.length) {
      err.textContent = "Missing document: " + missingDocs.join(", ") +
        ". Please upload all required documents to complete registration.";
      /* Each missing item turns red and names itself, so the driver
         sees at once which uploads are still needed. */
      missingFields.forEach(function (field) {
        markDocItemError(field, missingDocMessage(field));
      });
      return;
    }
    /* Owner decision 2026-11-17: the profile photo must be
       passport-style — portrait, large enough to show the face
       properly ("Bas face proper dikhna"). Pre-check here for a
       fast, clear message; the server enforces the same rules. */
    checkProfilePhoto($("file-profile_photo").files[0], function (photoError) {
      if (photoError) {
        err.textContent = photoError;
        markDocItemError("profile_photo", photoError);
        return;
      }
      submitRegistration();
    });

    function submitRegistration() {
    var fd = new FormData();
    fd.append("name", name);
    fd.append("phone", phone);
    fd.append("email", email);
    fd.append("password", password);
    fd.append("password_confirm", passwordConfirm);
    fd.append("state", stateName);
    fd.append("city", cityName);
    fd.append("car_model", carModel);
    fd.append("car_year", carYear);
    fd.append("car_colour", carColour);
    fd.append("plate", plate);
    fd.append("bank_account_number", acct);
    fd.append("bank_routing_number", routing);
    /* Referral link capture: when registration arrived via
       /driver?ref=CODE, the referrer's code rides along in a hidden
       field — the form itself has no extra field or step. An
       unknown code is ignored by the server, never blocks. */
    if (state.pendingReferralCode) {
      fd.append("referral_code", state.pendingReferralCode);
    }
    requiredFields.forEach(function (field) {
      var input = $("file-" + field);
      if (input && input.files && input.files[0]) fd.append(field, input.files[0]);
      /* Expiry date for documents that have one (owner decision
         2026-11-19): sent as expiry_<doc_type>. The server rejects
         a past date, so an expired document never registers. */
      var expiryInput = $("expiry-" + field);
      if (expiryInput && expiryInput.value) {
        var docType = null;
        Object.keys(FIELD_FOR_DOC_TYPE).forEach(function (t) {
          if (FIELD_FOR_DOC_TYPE[t] === field) docType = t;
        });
        if (docType) fd.append("expiry_" + docType, expiryInput.value);
      }
    });
    var btn = $("register-submit");
    btn.disabled = true;
    btn.textContent = "Registering…";
    fetch("/api/drivers/register", { method: "POST", body: fd })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        btn.textContent = "Complete registration";
        if (!res.ok || !res.j.token) {
          var serverError = (res.j && (res.j.error || res.j.message)) || "Registration could not be completed. Please check your details and try again.";
          err.textContent = serverError;
          /* A document error also turns its own item red; any other
             error leaves the items alone. */
          markDocErrorsFromServer(serverError, requiredFields);
          return;
        }
        saveToken(res.j.token);
        state.pendingReferralCode = null;
        enterApp(unwrapDriver(res.j) || {});
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "Complete registration";
        err.textContent = "Could not reach the service. Please check your connection and try again.";
      });
    }
  });

  /* ---------- Email + password sign-in ---------- */
  /* Owner decision 2026-11-18, complete sign-in process: the
     sign-in is email + password. On success the server re-issues
     the token, saved on this device, so signing in on a new phone
     signs the old one out. On failure the server's generic error
     is shown — it never says whether the email or the password
     was wrong. */
  $("signin-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("signin-error");
    err.textContent = "";
    var email = $("signin-email").value.trim();
    var password = $("signin-password").value;
    if (!email || !password) { err.textContent = "Please enter your email and password."; return; }
    var btn = $("signin-submit");
    btn.disabled = true;
    fetch("/api/drivers/me/signin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok || !res.j.token) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Email or password is incorrect.";
          return;
        }
        saveToken(res.j.token);
        /* Sign-in returns only id + name: fetch the full record so the
           Documents and Profile tabs are populated on this device. */
        fetch("/api/drivers/me", { headers: authHeaders() })
          .then(function (r) { return r.json(); })
          .then(function (j) { enterApp(unwrapDriver(j) || unwrapDriver(res.j) || {}); })
          .catch(function () { enterApp(unwrapDriver(res.j) || {}); });
      })
      .catch(function () {
        btn.disabled = false;
        err.textContent = "Could not reach the service. Please try again.";
      });
  });

  /* ---------- Forgot password ---------- */
  /* The driver enters an email and always sees the same message,
     whether or not the email is registered — the server never
     reveals that. The reset link is queued to the owner-dashboard
     outbox (recorded, not sent) until an email service is
     connected, so today the owner shares the link with the
     driver. */
  $("forgot-link").addEventListener("click", function () {
    hide($("signin-form"));
    hide($("forgot-link"));
    show($("forgot-form"));
  });
  $("forgot-back-link").addEventListener("click", function () {
    hide($("forgot-form"));
    show($("signin-form"));
    show($("forgot-link"));
  });
  $("forgot-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var msg = $("forgot-message");
    msg.textContent = "";
    var email = $("forgot-email").value.trim();
    if (!email) { msg.textContent = "Please enter your email."; return; }
    var btn = $("forgot-submit");
    btn.disabled = true;
    fetch("/api/drivers/me/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email })
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        btn.disabled = false;
        msg.textContent = (j && j.message) || "If an account exists for that email, password reset instructions have been sent.";
      })
      .catch(function () {
        btn.disabled = false;
        msg.textContent = "Could not reach the service. Please try again.";
      });
  });

  /* ---------- Password reset via link ---------- */
  /* A /driver?reset=<token> link opens the set-new-password form
     instead of the normal sign-in view (see boot()). The token
     itself is only ever sent back to the server — it is never
     shown on screen or logged. */
  function showResetForm(resetToken) {
    state.resetToken = resetToken;
    hide($("signin-form"));
    hide($("forgot-link"));
    hide($("forgot-form"));
    hide($("show-register-link"));
    var heading = document.querySelector("#screen-login > h2");
    if (heading) hide(heading);
    show($("reset-block"));
    showScreen("login");
  }
  $("reset-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("reset-error");
    err.textContent = "";
    var password = $("reset-password").value;
    var passwordConfirm = $("reset-password-confirm").value;
    if (password.length < 6) { err.textContent = "Password must be at least 6 characters."; return; }
    if (password !== passwordConfirm) { err.textContent = "Passwords do not match."; return; }
    var btn = $("reset-submit");
    btn.disabled = true;
    fetch("/api/drivers/me/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: state.resetToken, password: password, password_confirm: passwordConfirm })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "This reset link is invalid or has expired.";
          return;
        }
        hide($("reset-form-fields"));
        show($("reset-done"));
      })
      .catch(function () {
        btn.disabled = false;
        err.textContent = "Could not reach the service. Please try again.";
      });
  });
  $("reset-back-btn").addEventListener("click", function () {
    /* Reload without the query string, so the used token leaves the
       address bar and the normal sign-in view returns. */
    window.location.assign("/driver");
  });

  /* ---------- New driver registration ---------- */
  /* Owner decision 2026-11-18: the login screen carries a
     "New driver registration" link at the bottom; only tapping it
     opens the registration form. Signed-in drivers never see it. */
  $("show-register-link").addEventListener("click", function () {
    showScreen("register");
  });

  /* ---------- Availability ---------- */
  /* Suspension (owner rule 2026-11-18): after a fault emergency
     cancel, the driver app is blocked for 48 hours. Sign-in still
     works so the driver sees this notice with the exact end
     date/time; he cannot go available and gets no offers until
     it lifts. The end time comes from /api/drivers/me. */
  function suspensionEnd() {
    var until = state.driver && state.driver.suspended_until;
    if (!until) return null;
    var d = new Date(until);
    if (isNaN(d.getTime()) || d.getTime() <= Date.now()) return null;
    return d;
  }
  function renderSuspension() {
    var banner = $("suspension-banner");
    var end = suspensionEnd();
    if (!end) { hide(banner); return; }
    var when = end.toLocaleString(undefined, {
      month: "long", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit"
    });
    banner.textContent = "Your driver app is paused until " + when + ". You will not get job offers until then.";
    show(banner);
  }
  function refreshDriverState() {
    return fetch("/api/drivers/me", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var d = unwrapDriver(j);
        if (d) {
          state.driver = d;
          state.available = !!d.available;
          renderAvailability();
        }
      })
      .catch(function () { /* leave the toggle as it was */ });
  }
  /* ---------- Document expiry notice ---------- */
  /* Owner decision 2026-11-19: a document expiring within 10 days
     warns here; an expired document pauses the registration (no
     offers, cannot go available) until the driver uploads a new one
     from the Documents screen — the block then lifts automatically.
     The dates come from /api/drivers/me. */
  function renderExpiry() {
    var banner = $("expiry-banner");
    var d = state.driver || {};
    var expired = d.expired_docs || [];
    var expiring = d.expiring_docs || [];
    if (!expired.length && !expiring.length) { hide(banner); return; }
    banner.classList.remove("expired");
    var text = "";
    if (expired.length) {
      banner.classList.add("expired");
      text = "Your registration is paused — your " +
        expired.map(function (x) { return x.label + " (expired " + x.expires_on + ")"; }).join(", ") +
        " expired. Upload a new, valid document to reactivate it.";
    } else {
      text = "Your " +
        expiring.map(function (x) {
          return x.label + " expires " + x.expires_on +
            (x.days_left === 0 ? " (today)" : x.days_left === 1 ? " (tomorrow)" : " (in " + x.days_left + " days)");
        }).join(", ") +
        ". Upload a new document soon so your registration stays active.";
    }
    banner.textContent = text;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-ghost";
    btn.textContent = "View documents";
    btn.addEventListener("click", function () { showScreen("documents"); });
    banner.appendChild(btn);
    show(banner);
  }
  /* Bare button only (owner decision, voice call 2026-11-21
     ~03:04 EST): the availability card and all its text lines are
     gone — no state line, no notes. The button label alone conveys
     the state (Go online / Go offline). Suspension and expiry-block
     explanations still show in the banners at the top of the home
     screen (renderSuspension / renderExpiry). */
  function renderAvailability() {
    var btn = $("avail-toggle");
    renderSuspension();
    renderExpiry();
    if (suspensionEnd()) {
      btn.textContent = "Go online";
      btn.classList.remove("on");
      btn.disabled = true;
      return;
    }
    /* An expired document pauses the registration (owner decision
       2026-11-19): the toggle stays off until the driver uploads a
       new, valid document from the Documents screen. */
    if (state.driver && state.driver.expiry_blocked) {
      btn.textContent = "Go online";
      btn.classList.remove("on");
      btn.disabled = true;
      return;
    }
    btn.disabled = false;
    if (state.available) {
      btn.textContent = "Go offline";
      btn.classList.add("on");
    } else {
      btn.textContent = "Go online";
      btn.classList.remove("on");
    }
  }
  $("avail-toggle").addEventListener("click", function () {
    unlockAudio();
    var next = !state.available;
    fetch("/api/drivers/me/availability", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ available: next })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          /* e.g. suspended: re-read the driver record so the
             suspension banner shows instead of a flipped toggle. */
          refreshDriverState();
          return;
        }
        state.available = next;
        renderAvailability();
        refreshOffers();
      })
      .catch(function () { /* leave the toggle as it was */ });
  });

  /* ---------- New-offer tone ---------- */
  /* Browsers only allow sound after the driver has tapped something,
     so the audio context is unlocked on any tap on the page. The tone
     is a short chime made with the Web Audio API — no audio file
     needed. A new offer repeats that chime for 30 seconds so the
     driver cannot miss it; it stops the moment he accepts or
     declines, when the offer disappears, or when the 30 seconds are
     up. The tone only plays while this page is open in the browser. */
  function unlockAudio() {
    try {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      if (!state.audioCtx) state.audioCtx = new AC();
      if (state.audioCtx.state === "suspended") state.audioCtx.resume();
    } catch (e) { /* audio unavailable: offers still show silently */ }
  }
  /* Any tap on the page unlocks audio, so a driver who never taps the
     availability toggle still hears the new-offer tone. */
  document.addEventListener("pointerdown", unlockAudio);

  /* Offer IDs already alerted to, kept in localStorage across page
     refreshes. Without this, a refresh wiped the in-memory set and
     the first poll only "primed" — an offer already on screen would
     never ring. With it, the first poll after a refresh rings for
     genuinely new offers only, and never re-rings an old one. */
  function loadSeenOfferIds() {
    try {
      var raw = window.localStorage.getItem(SEEN_OFFERS_KEY);
      var ids = raw ? JSON.parse(raw) : [];
      var seen = {};
      if (Array.isArray(ids)) {
        ids.forEach(function (id) { seen[id] = true; });
      }
      state.seenOfferIds = seen;
    } catch (e) { state.seenOfferIds = {}; }
  }
  function saveSeenOfferIds() {
    try {
      var ids = Object.keys(state.seenOfferIds);
      /* Booking IDs grow over time, so keeping the newest entries
         bounds the stored list; old offers never come back. */
      if (ids.length > MAX_SEEN_OFFERS) ids = ids.slice(ids.length - MAX_SEEN_OFFERS);
      window.localStorage.setItem(SEEN_OFFERS_KEY, JSON.stringify(ids));
    } catch (e) { /* private mode: ringing still works for this session */ }
  }
  function clearSeenOfferIds() {
    state.seenOfferIds = {};
    try { window.localStorage.removeItem(SEEN_OFFERS_KEY); } catch (e) { /* ignore */ }
  }

  /* One chime burst: the three-note pattern plus a vibration. */
  function playOfferTone() {
    try {
      unlockAudio();
      var ctx = state.audioCtx;
      if (!ctx) return;
      var notes = [880, 1174.66, 880];
      notes.forEach(function (freq, i) {
        var t = ctx.currentTime + i * 0.18;
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.16);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.18);
      });
      if (navigator.vibrate) navigator.vibrate([180, 80, 180]);
    } catch (e) { /* keep silent on failure */ }
  }

  /* Ring for up to 30 seconds for the given offer IDs. A second new
     offer arriving while already ringing extends the window to 30
     seconds from its arrival; an offer already alerted to never
     starts the tone again. */
  function startOfferTone(ids) {
    ids.forEach(function (id) { state.toneOfferIds[id] = true; });
    state.toneStopAt = Date.now() + TONE_DURATION_MS;
    if (state.toneTimer) return;
    playOfferTone();
    state.toneTimer = setInterval(function () {
      if (Date.now() >= state.toneStopAt) { stopOfferTone(); return; }
      playOfferTone();
    }, TONE_REPEAT_MS);
  }
  function stopOfferTone() {
    if (state.toneTimer) clearInterval(state.toneTimer);
    state.toneTimer = null;
    state.toneOfferIds = {};
    state.toneStopAt = 0;
    try { if (navigator.vibrate) navigator.vibrate(0); } catch (e) { /* ignore */ }
  }

  /* ---------- Job offers (no amounts while prices are being updated) ---------- */
  function startOffersPolling() {
    if (state.offersTimer) clearInterval(state.offersTimer);
    state.offersTimer = setInterval(function () {
      if (!$("screen-home").classList.contains("hidden") && !state.trip) {
        refreshOffers();
      }
    }, 5000);
  }
  function refreshOffers() {
    if (!state.token) return;
    fetch("/api/drivers/me/offers", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = Array.isArray(j) ? j : (j.offers || []);
        /* Ring for every offer the driver has never been alerted to —
           including on the very first poll after a refresh, because
           the seen set is loaded from storage before polling starts.
           An offer already alerted to never rings again, even if it
           leaves the list and comes back. */
        var freshIds = [];
        list.forEach(function (o) {
          var id = offerId(o);
          if (!state.seenOfferIds[id]) {
            state.seenOfferIds[id] = true;
            freshIds.push(id);
          }
        });
        if (freshIds.length) {
          saveSeenOfferIds();
          startOfferTone(freshIds);
        }
        /* Stop ringing when every offer being rung for has gone. */
        if (state.toneTimer) {
          var present = {};
          list.forEach(function (o) { present[offerId(o)] = true; });
          var anyLeft = false;
          for (var ringingId in state.toneOfferIds) {
            if (present[ringingId]) { anyLeft = true; break; }
          }
          if (!anyLeft) stopOfferTone();
        }
        renderOffers(list);
      })
      .catch(function () { /* keep the current list on a failed check */ });
  }
  function offerId(o) { return o.booking_id || o.id; }
  /* Route as two separate blocks (owner 2026-11-23): 'Pick up' and
     'Drop off' used to run together on one line, so the two addresses
     were hard to tell apart at a glance. Each leg is now its own
     block, with a down arrow on its own line between them. Hourly
     rides have no drop-off, so only the pickup block shows.
     Addresses stay escaped. */
  function routeHtml(pickup, dropoff) {
    var html = '<div class="route-leg"><span class="route-label">Pick up</span> ' + esc(pickup || "") + '</div>';
    if (dropoff) html += '<div class="route-sep" aria-hidden="true">↓</div>' +
      '<div class="route-leg"><span class="route-label">Drop off</span> ' + esc(dropoff) + '</div>';
    return html;
  }
  function renderOffers(list) {
    var box = $("offers-list");
    /* The job stays put until the driver accepts or declines it: when
       nothing about the offers changed, leave the cards untouched so
       the list never flickers or rebuilds under the driver's tap. */
    var sig = list.map(function (o) { return offerId(o); }).join("|");
    if (sig === state.lastOffersSig) return;
    state.lastOffersSig = sig;
    box.innerHTML = "";
    if (!list.length) { show($("offers-empty")); return; }
    hide($("offers-empty"));
    list.forEach(function (o) {
      var card = document.createElement("div");
      card.className = "offer";
      var route = routeHtml(o.pickup, o.dropoff);
      var when = [o.date, o.time].filter(Boolean).join(" · ");
      var cls = classLabelFor(o);
      if (cls) when += (when ? " · " : "") + cls;
      if (o.ride_type === "hourly") when += (when ? " · " : "") + "By the hour" + (o.hours ? " · " + o.hours + " hour(s)" : "");
      else if (o.is_return) when += (when ? " · " : "") + "Return trip";
      /* PAUSED (owner decision 2026-11-20): offers show pickup,
         drop-off and time only — no earnings, no toll. */
      var html = '<div class="route">' + route + "</div>" +
        '<div class="when">' + esc(when) + "</div>";
      if (o.route_url) {
        html += '<a class="route-link" href="' + esc(o.route_url) + '" target="_blank" rel="noopener">Google Maps ↗</a>';
      }
      if (o.route_waze_url) {
        html += '<a class="route-link" href="' + esc(o.route_waze_url) + '" target="_blank" rel="noopener">Waze ↗</a>';
      }
      html += '<div class="offer-actions">' +
        '<button type="button" class="btn-accept">Accept</button>' +
        '<button type="button" class="btn-decline">Decline</button></div>';
      card.innerHTML = html;
      card.querySelector(".btn-accept").addEventListener("click", function () { respondToOffer(offerId(o), "accept"); });
      card.querySelector(".btn-decline").addEventListener("click", function () { respondToOffer(offerId(o), "decline"); });
      box.appendChild(card);
    });
  }
  function respondToOffer(id, action) {
    /* The driver answered: stop the tone at once, for accept and
       decline alike, without waiting for the next poll. */
    stopOfferTone();
    fetch("/api/drivers/me/offers/" + encodeURIComponent(id) + "/" + action, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({})
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (action === "decline") { refreshOffers(); return; }
        if (!res.ok) { refreshOffers(); return; }
        var b = res.j.booking || res.j;
        state.trip = tripFromBooking(b, id);
        state.stageIndex = 0;
        renderTrip();
        showScreen("trip");
        openTripChatOnAccept();
      })
      .catch(function () { refreshOffers(); });
  }

  /* Owner rule 2026-11-18 (voice call: "Driver jaisa trip accept
     karega, jab uske paas chat box khulna chahiye"): the moment the
     driver accepts a trip, the chat box must OPEN for him. The chat
     sits at the bottom of the trip screen, below the fold, and
     showScreen lands at the top — so scroll the chat into view at
     once, with no extra tap or scroll from the driver. The box
     itself is always expanded; only its position needs bringing
     into view. Called ONLY from the accept path: restoring an
     active trip on reload must not yank the driver to the chat. */
  function openTripChatOnAccept() {
    var chat = $("trip-chat");
    if (chat) chat.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* Staged navigation destination (Uber-driver-style): until the
     customer is picked up, navigation goes TO THE PICKUP from the
     driver's current location; only after pickup does it go to the
     drop-off. stageIndex counts completed stages, so the customer
     is picked up once it reaches 3 (the "complete" stage is
     current, server status in_progress). Hourly rides have no
     drop-off: after pickup there is nowhere to navigate, so no
     destination is returned. This helper feeds ONLY the navigation
     chooser that pops on "Head to pickup" / "Start trip" — the
     trip screen itself shows no Google Maps / Waze links (owner
     decision 2026-11-20: removed from the top of the trip screen).
     The offer card is untouched: its links keep previewing the
     whole trip (pickup -> drop-off) while the driver decides.
     Google Maps gets a destination with no origin, so it routes
     from the driver's current location; Waze navigates to the
     single destination from the current location. */
  function tripNavDestination(stageIndex, pickup, dropoff) {
    if (stageIndex < 3) return pickup || null;
    return dropoff || null;
  }

  /* Navigation chooser (owner request 2026-11-17): tapping "Head
     to pickup" or "Start trip" pops a small chooser offering Google
     Maps or Waze, so Maps opens straight to the pickup or the
     drop-off without the driver hunting for the links. It appears
     ONLY on those two stage advances — never on "arrived" or on
     completion — and dismissing it changes nothing: the stage has
     already advanced. Owner order 2026-11-23 ("Not now nahi
     rehna"): there is NO "Not now" button — the driver picks
     Google Maps or Waze; tapping outside the card still dismisses
     it without changing the trip. Owner order 2026-11-23 ~13:25
     EST ("Chooser pe X button daal do"): a VISIBLE close (×)
     button sits top-right of the card and dismisses the chooser
     without opening any map — the owner reported tapping outside
     the card does not dismiss it on his phone, so the close must
     be a real button, not only a backdrop tap. The overlay also
     carries cursor: pointer in CSS: iOS Safari only delivers tap
     (click) events to a plain div reliably when it looks clickable,
     which is the likely cause of the dead backdrop tap. The
     destination reuses tripNavDestination, so hourly rides (no
     drop-off) never get a drop-off chooser. The external URL opens
     from the chooser button's own tap handler, a direct user
     gesture, so mobile browsers do not block it. */
  function navChooserUrls(dest) {
    return {
      google: "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(dest),
      waze: "https://waze.com/ul?q=" + encodeURIComponent(dest) + "&navigate=yes"
    };
  }
  function showNavChooser(dest, title) {
    if (!dest) return;
    var urls = navChooserUrls(dest);
    $("nav-chooser-title").textContent = title;
    $("nav-chooser-dest").textContent = dest;
    $("nav-chooser-google").onclick = function () { hideNavChooser(); window.open(urls.google, "_blank", "noopener"); };
    $("nav-chooser-waze").onclick = function () { hideNavChooser(); window.open(urls.waze, "_blank", "noopener"); };
    $("nav-chooser-x").onclick = function () { hideNavChooser(); };
    show($("nav-chooser-overlay"));
  }
  function hideNavChooser() {
    hide($("nav-chooser-overlay"));
  }
  function maybeShowNavChooser(advancedStage) {
    var t = state.trip;
    if (!t) return;
    var dest = tripNavDestination(state.stageIndex, t.pickup, t.dropoff);
    if (advancedStage === "en_route") {
      showNavChooser(dest, "Navigate to pickup");
    } else if (advancedStage === "start") {
      showNavChooser(dest, "Navigate to drop-off");
    }
  }
  $("nav-chooser-overlay").addEventListener("click", function (e) {
    if (e.target === $("nav-chooser-overlay")) hideNavChooser();
  });

  /* ---------- Trip screen ---------- */
  function renderTrip() {
    var t = state.trip;
    if (!t) return;
    var route = routeHtml(t.pickup, t.dropoff);
    $("trip-route").innerHTML = route;
    var when = [t.date, t.time].filter(Boolean).join(" · ");
    var cls = classLabelFor(t);
    if (cls) when += (when ? " · " : "") + cls;
    if (t.ride_type === "hourly") when += (when ? " · " : "") + "By the hour" + (t.hours ? " · " + t.hours + " hour(s)" : "");
    else if (t.is_return) when += (when ? " · " : "") + "Return trip";
    $("trip-when").textContent = when;
    var cust = "";
    if (t.customer_name) cust += esc(t.customer_name);
    if (t.customer_phone) {
      cust += (cust ? " · " : "") + '<a href="tel:' + esc(t.customer_phone.replace(/[^+0-9]/g, "")) + '">' + esc(t.customer_phone) + "</a>";
    }
    $("trip-customer").innerHTML = cust;
    /* Flight details for airport trips: flight number, airline name and
       terminal only — never miles, fare, or any other money figure.
       The track link appears only for airport pickups, so the driver
       can check when the flight lands. */
    var flightEl = $("trip-flight");
    if (t.flight_number) {
      var flightText = "Flight: " + t.flight_number;
      if (t.airline_name) flightText += " · " + t.airline_name;
      if (t.terminal) flightText += " · " + t.terminal;
      var flightHtml = esc(flightText);
      if (t.airport_pickup) {
        flightHtml += ' <a class="flight-track-link" href="' + esc("https://www.google.com/search?q=" + encodeURIComponent(t.flight_number + " flight status")) + '" target="_blank" rel="noopener">Track flight ↗</a>';
      }
      flightEl.innerHTML = flightHtml;
      show(flightEl);
    } else {
      flightEl.textContent = "";
      hide(flightEl);
    }
    /* PAUSED (owner decision 2026-11-20): no earnings shown on the
       trip screen. */
    $("trip-earnings").innerHTML = "";
    /* Digital name sign: every pickup. The driver holds the phone
       up so the customer can spot their name. (Owner 2026-11-24:
       "Name sign mein customer ka naam aana chaiye" — was airport
       pickups only.) */
    var signBtn = $("trip-namesign-btn");
    if (t.customer_name) {
      show(signBtn);
    } else {
      hide(signBtn);
    }
    renderStages();
    startNoShowTimer();
    startReminderPolling();
    startChatPolling();
    $("trip-error").textContent = "";
  }
  /* ---------- Arrival / completion proximity gates ---------- */
  /* Owner rule 2026-11-17 (fraud prevention): "I have arrived" only
     within 100 m of the pickup, "Complete trip" only within 100 m
     of the drop-off. Hourly rides have no drop-off, so their
     completion stays ungated; a trip without stored coordinates
     for the relevant end cannot be verified and stays ungated too.
     The server enforces the same rule on any position it is given;
     this is the visible side of it, and the tap-time check below
     sends a fresh GPS position with every gated advance. No
     location, no silent bypass: the button stays disabled and the
     note explains that location is needed.
     Owner decision 2026-11-20 (voice call): the gate does not apply
     to the owner (Azher Mohammed) or Sana Baga — the same two
     drivers as the Model 3 exception (same three emails). For them
     the gate is skipped entirely: the button stays enabled without
     a location and the advance is sent with no position. Every
     other driver keeps the gate exactly as it is. */
  var LOCATION_EXEMPT_EMAILS = [
    "m.azherahmed1@gmail.com",
    "ahmedazher476@gmail.com",
    "sanabaga12@gmail.com"
  ];
  function locationExempt() {
    var email = ((state.driver && state.driver.email) || "").trim().toLowerCase();
    return LOCATION_EXEMPT_EMAILS.indexOf(email) !== -1;
  }
  var PROXIMITY_GATE_METERS = 100;
  function haversineMeters(lat1, lng1, lat2, lng2) {
    var r = 6371000;
    var p1 = lat1 * Math.PI / 180, p2 = lat2 * Math.PI / 180;
    var dphi = (lat2 - lat1) * Math.PI / 180;
    var dlambda = (lng2 - lng1) * Math.PI / 180;
    var a = Math.sin(dphi / 2) * Math.sin(dphi / 2) +
      Math.cos(p1) * Math.cos(p2) * Math.sin(dlambda / 2) * Math.sin(dlambda / 2);
    return 2 * r * Math.asin(Math.sqrt(a));
  }
  function gateTarget() {
    /* Exempt drivers (owner + Sana, 2026-11-20) skip the gate
       entirely: no target, so the button stays enabled and the
       advance is sent with no position. */
    if (locationExempt()) return null;
    var current = STAGES[state.stageIndex];
    var t = state.trip;
    if (!t) return null;
    if (current === "arrived") {
      if (t.pickup_lat === null || t.pickup_lng === null) return null;
      return { lat: t.pickup_lat, lng: t.pickup_lng, kind: "pickup" };
    }
    if (current === "complete") {
      if (t.ride_type === "hourly") return null;
      if (t.dropoff_lat === null || t.dropoff_lng === null) return null;
      return { lat: t.dropoff_lat, lng: t.dropoff_lng, kind: "dropoff" };
    }
    return null;
  }
  function gateMessage(target) {
    return target.kind === "pickup"
      ? "You must be at the pickup location to mark arrived."
      : "You must be at the drop-off location to complete the trip.";
  }
  function refreshGateNote() {
    var btn = $("trip-next-btn");
    var note = $("trip-gate-note");
    var target = gateTarget();
    if (!target) {
      hide(note);
      if (!state.advancing) btn.disabled = false;
      return;
    }
    if (!("geolocation" in navigator)) {
      note.textContent = "Location is needed to mark this step. This device does not support location sharing.";
      show(note);
      if (!state.advancing) btn.disabled = true;
      return;
    }
    if (!state.lastPosition) {
      note.textContent = state.locationError
        ? "Location is needed to mark this step. Please allow location access and try again."
        : "Waiting for your location…";
      show(note);
      if (!state.advancing) btn.disabled = true;
      return;
    }
    var d = haversineMeters(state.lastPosition.lat, state.lastPosition.lng, target.lat, target.lng);
    if (d <= PROXIMITY_GATE_METERS) {
      hide(note);
      if (!state.advancing) btn.disabled = false;
    } else {
      note.textContent = gateMessage(target);
      show(note);
      if (!state.advancing) btn.disabled = true;
    }
  }
  function getFreshPosition(cb) {
    if (!("geolocation" in navigator)) { cb(null); return; }
    try {
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          state.lastPosition = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          state.locationError = false;
          cb(state.lastPosition);
        },
        function () { state.locationError = true; cb(null); },
        { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 });
    } catch (e) { cb(null); }
  }
  function renderStages() {
    var items = document.querySelectorAll("#stage-list li");
    items.forEach(function (li, i) {
      var tick = li.querySelector(".tick");
      li.classList.remove("done", "current");
      if (i < state.stageIndex) { li.classList.add("done"); tick.textContent = "✓"; }
      else if (i === state.stageIndex) { li.classList.add("current"); tick.textContent = "●"; }
      else { tick.textContent = ""; }
    });
    var current = STAGES[state.stageIndex];
    /* Slide-to-confirm label (owner 2026-11-22): the button holds a
       label span and a thumb, so the stage name goes into the label
       span — setting textContent on the button would wipe the
       thumb. */
    var stageLabel = document.querySelector("#trip-next-btn .slide-label");
    if (stageLabel) { stageLabel.textContent = STAGE_BUTTON[current] || "Continue"; }
    else { $("trip-next-btn").textContent = STAGE_BUTTON[current] || "Continue"; }
    if (current === "complete") {
      show($("waiting-field"));
      /* Extra miles apply to one-way rides only, never hourly. */
      if (state.trip && state.trip.ride_type !== "hourly") { show($("extra-miles-field")); }
      else { hide($("extra-miles-field")); }
    } else {
      hide($("waiting-field"));
      hide($("extra-miles-field"));
    }
    refreshNoShowButton();
    refreshCancelButton();
    refreshGateNote();
  }
  /* Emergency cancel (owner rule 2026-11-18, SUPERSEDES the
     2026-11-17 lock that hid the button): the Cancel button ALWAYS
     stays visible. More than 2 hours out, cancelling works as
     before. Once pickup is within 2 hours, tapping Cancel opens
     the reason step instead: the driver must pick a reason, which
     is checked automatically. The server enforces the same rule
     with a 409, so this is only the visible side of it. When the
     pickup time is missing or unparseable the plain confirm is
     used and the server decides. */
  function refreshCancelButton() {
    var note = $("trip-cancel-note");
    var t = state.trip;
    var locked = false;
    if (t && t.date && t.time) {
      var pickup = new Date(t.date + "T" + t.time);
      if (!isNaN(pickup.getTime()) && pickup.getTime() - Date.now() <= 2 * 60 * 60000) {
        locked = true;
      }
    }
    state.cancelLocked = locked;
    note.textContent = locked
      ? "Pickup is within 2 hours. You can still cancel, but you must give a reason."
      : "If you cancel, the job goes to the next driver automatically.";
  }
  /* Customer no-show is only offered once the driver has waited the
     FULL free waiting time (60 min at airports, else 15) from the
     pickup time, while heading to or waiting at pickup. stageIndex
     counts completed stages, so en_route is 1 and arrived is 2 —
     matching the server's stage check. */
  function refreshNoShowButton() {
    var btn = $("trip-noshow-btn");
    var t = state.trip;
    if (!t || (state.stageIndex !== 1 && state.stageIndex !== 2) || !t.date || !t.time) {
      hide(btn);
      return;
    }
    var allowance = (typeof t.free_waiting_minutes === "number") ? t.free_waiting_minutes : 15;
    var pickup = new Date(t.date + "T" + t.time);
    if (isNaN(pickup.getTime())) { hide(btn); return; }
    if (Date.now() >= pickup.getTime() + allowance * 60000) { show(btn); }
    else { hide(btn); }
  }
  function startNoShowTimer() {
    if (state.noShowTimer) clearInterval(state.noShowTimer);
    state.noShowTimer = setInterval(function () {
      if (state.trip) { refreshNoShowButton(); refreshCancelButton(); }
    }, 30000);
  }
  function stopNoShowTimer() {
    if (state.noShowTimer) clearInterval(state.noShowTimer);
    state.noShowTimer = null;
  }
  /* 1-hour pickup reminder (owner decision 2026-11-18): while the
     trip screen is open, check every 30 seconds whether the accepted
     ride starts within the hour; if so, show the gold banner at the
     top of the trip screen. The server decides (same window as the
     queued email/SMS reminder) and the banner shows pickup time +
     addresses only — never miles, fare, or total. A missed check is
     harmless; the next one follows. When the banner first appears
     for a booking it plays ONE burst of the new-offer chime
     (playOfferTone, which unlocks audio and fails silently exactly
     as the offer path does); later polls while the banner is
     already showing for the same booking stay silent. */
  function refreshPickupReminder() {
    if (!state.trip) { hide($("trip-reminder-banner")); state.reminderChimedBookingId = null; return; }
    fetch("/api/drivers/me/pickup-reminder", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var banner = $("trip-reminder-banner");
        var rem = j && j.reminder;
        if (!rem || !state.trip || rem.booking_id !== state.trip.id) { hide(banner); state.reminderChimedBookingId = null; return; }
        var wasHidden = banner.classList.contains("hidden");
        var text = "Your ride starts in about an hour — pickup " + rem.date + " at " + rem.time + " from " + rem.pickup;
        if (rem.ride_type !== "hourly" && rem.dropoff) text += " to " + rem.dropoff;
        text += ".";
        banner.textContent = text;
        show(banner);
        if (wasHidden || state.reminderChimedBookingId !== rem.booking_id) {
          state.reminderChimedBookingId = rem.booking_id;
          playOfferTone();
        }
      })
      .catch(function () { /* keep the current banner on a failed check */ });
  }
  function startReminderPolling() {
    stopReminderPolling();
    refreshPickupReminder();
    state.reminderTimer = setInterval(function () {
      if (state.trip && !$("screen-trip").classList.contains("hidden")) refreshPickupReminder();
    }, 30000);
  }
  function stopReminderPolling() {
    if (state.reminderTimer) clearInterval(state.reminderTimer);
    state.reminderTimer = null;
  }

  /* ---------- Digital name sign (every pickup) ---------- */
  $("trip-namesign-btn").addEventListener("click", function () {
    if (!state.trip || !state.trip.customer_name) return;
    $("namesign-name").textContent = state.trip.customer_name;
    show($("namesign-overlay"));
  });
  $("namesign-close").addEventListener("click", function () {
    hide($("namesign-overlay"));
  });
  $("namesign-overlay").addEventListener("click", function (e) {
    if (e.target === $("namesign-overlay")) hide($("namesign-overlay"));
  });

  /* ---------- In-app chat with the customer (text only) ---------- */
  /* Simple polling, no SMS. Messages carry text only — the chat
     never shows any money figure, and the driver still sees only his
     own earnings elsewhere on this screen. Declared chat language:
     one picker, plain labels, default English. The server
     translates each message ONCE at send time into the other side's
     picked language and stores it; reads never translate. Same
     codes/labels as the customer picker and
     translation.CHAT_LANGUAGES — keep all three in step. */
  var CHAT_LANGUAGES = ["en", "ur-Latn", "es", "fr", "ar", "hi", "bn", "pt"];
  var CHAT_LANG_KEY = "noel-driver-chat-language";
  function validChatLanguage(v) {
    return CHAT_LANGUAGES.indexOf(v) !== -1 ? v : "en";
  }
  function initChatLanguage(driver) {
    var saved = null;
    try { saved = window.localStorage.getItem(CHAT_LANG_KEY); } catch (e) { /* private mode */ }
    state.chatLanguage = validChatLanguage((driver && driver.chat_language) || saved || "en");
    var sel = $("trip-chat-language");
    if (sel) sel.value = state.chatLanguage;
  }
  function saveChatLanguage() {
    var sel = $("trip-chat-language");
    if (!sel) return;
    state.chatLanguage = validChatLanguage(sel.value);
    try { window.localStorage.setItem(CHAT_LANG_KEY, state.chatLanguage); } catch (e) { /* private mode */ }
    /* Persist on the driver record so the customer's replies are
       translated into the picked language. Failures are silent:
       the picker value still travels with every send and poll. */
    fetch("/api/drivers/me/chat-language", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ language: state.chatLanguage })
    }).catch(function () { /* keep chatting; language rides along anyway */ });
    state.lastChatSig = "";
    loadTripChat();
  }
  function chatMessagesUrl() {
    return "/api/drivers/me/trip/" + encodeURIComponent(state.trip.id) + "/messages";
  }
  function startChatPolling() {
    stopChatPolling();
    state.lastChatSig = "";
    loadTripChat();
    state.chatTimer = setInterval(function () {
      if (state.trip && !$("screen-trip").classList.contains("hidden")) loadTripChat();
    }, 4000);
  }
  function stopChatPolling() {
    if (state.chatTimer) clearInterval(state.chatTimer);
    state.chatTimer = null;
  }
  function loadTripChat() {
    if (!state.trip) return;
    fetch(chatMessagesUrl() + "?language=" + encodeURIComponent(state.chatLanguage), { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        renderTripChat(j.messages || []);
      })
      .catch(function () { /* keep the current messages on a failed check */ });
  }
  function renderTripChat(messages) {
    var sig = messages.map(function (m) { return m.id + ":" + (m.text || "").length + ":" + (m.translated ? "1" : "0"); }).join("|");
    if (sig === state.lastChatSig) return;
    state.lastChatSig = sig;
    var box = $("trip-chat-messages");
    box.innerHTML = "";
    if (!messages.length) {
      box.innerHTML = '<p class="chat-empty">No messages yet. Say hello to your customer here.</p>';
      return;
    }
    messages.forEach(function (m) {
      var div = document.createElement("div");
      var mine = m.sender === "driver";
      div.className = "chat-msg " + (mine ? "mine" : "theirs");
      div.innerHTML = '<span class="who">' + (mine ? "You" : "Customer") + "</span>" +
        '<span class="txt">' + esc(m.text) + "</span>";
      box.appendChild(div);
    });
    box.scrollTop = box.scrollHeight;
  }
  function sendTripChat() {
    if (!state.trip) return;
    var input = $("trip-chat-input");
    var text = input.value.trim();
    if (!text) return;
    var btn = $("trip-chat-send");
    btn.disabled = true;
    fetch(chatMessagesUrl(), {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ text: text, language: state.chatLanguage })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (res.ok) {
          input.value = "";
          loadTripChat();
        }
      })
      .catch(function () { btn.disabled = false; });
  }
  $("trip-chat-send").addEventListener("click", sendTripChat);
  $("trip-chat-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); sendTripChat(); }
  });
  var tripChatLang = $("trip-chat-language");
  if (tripChatLang) tripChatLang.addEventListener("change", saveChatLanguage);
  function postTripEvent(eventName, extra) {
    var payload = Object.assign({ event: eventName }, extra || {});
    return fetch("/api/drivers/me/trip/" + encodeURIComponent(state.trip.id) + "/event", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); });
  }
  /* Slide to confirm (owner 2026-11-22, Uber-style): the trip
     stage advances only when the driver slides the thumb to the
     end of the track — Head to pickup, I have arrived, Start trip,
     Complete trip. No more accidental taps. The slide calls the
     same advance path as the old tap: the 100 m location gate
     (Azher + Sana exemption), the Maps/Waze chooser and the stage
     flow are all unchanged. Keyboard Enter/Space on the focused
     slide completes it, so the control stays usable without a
     pointer. A disabled slide (location gate) cannot be dragged. */
  function fireStageAdvance() {
    var current = STAGES[state.stageIndex];
    if (!current || !state.trip || state.advancing) return;
    var btn = $("trip-next-btn");
    btn.disabled = true;
    state.advancing = true;
    var extra = {};
    if (current === "complete") {
      var w = parseInt($("waiting-minutes").value, 10);
      if (!isNaN(w) && w > 0) extra.waiting_minutes = w;
      if (state.trip && state.trip.ride_type !== "hourly") {
        var em = parseFloat($("extra-miles").value);
        if (!isNaN(em) && em > 0) extra.extra_miles = em;
      }
    }
    var target = gateTarget();
    if (!target) { advanceStage(current, extra, btn); return; }
    /* Gated step: verify a fresh GPS position before the server is
       asked, and send that position with the advance so the server
       can check it too. No location, no advance — the error
       explains that location is needed. */
    getFreshPosition(function (pos) {
      if (!pos) {
        state.advancing = false;
        btn.disabled = false;
        $("trip-error").textContent = "Location is needed to mark this step. Please allow location access and try again.";
        refreshGateNote();
        return;
      }
      var d = haversineMeters(pos.lat, pos.lng, target.lat, target.lng);
      if (d > PROXIMITY_GATE_METERS) {
        state.advancing = false;
        btn.disabled = false;
        $("trip-error").textContent = gateMessage(target);
        refreshGateNote();
        return;
      }
      extra.lat = pos.lat;
      extra.lng = pos.lng;
      advanceStage(current, extra, btn);
    });
  }
  var SLIDE_COMPLETE_FRACTION = 0.8;
  function wireTripSlide() {
    var btn = $("trip-next-btn");
    if (!btn) return;
    var thumb = btn.querySelector(".slide-thumb");
    var dragging = false, startX = 0, dragX = 0, maxDx = 0;
    function slideMax() {
      var track = btn.getBoundingClientRect().width;
      var tw = thumb ? thumb.getBoundingClientRect().width : 50;
      return Math.max(0, track - tw - 8);
    }
    function setThumb(x) {
      if (thumb) thumb.style.transform = "translateX(" + x + "px)";
    }
    function resetThumb() {
      if (!thumb) return;
      thumb.style.transition = "transform 0.18s ease";
      thumb.style.transform = "translateX(0)";
      setTimeout(function () { if (thumb) thumb.style.transition = ""; }, 200);
    }
    $("trip-next-btn").addEventListener("pointerdown", function (e) {
      if (btn.disabled || state.advancing || !state.trip) return;
      dragging = true;
      startX = e.clientX;
      dragX = 0;
      maxDx = slideMax();
      try { btn.setPointerCapture(e.pointerId); } catch (err) { /* older browsers */ }
      e.preventDefault();
    });
    $("trip-next-btn").addEventListener("pointermove", function (e) {
      if (!dragging) return;
      dragX = Math.max(0, Math.min(maxDx, e.clientX - startX));
      setThumb(dragX);
    });
    function finishDrag() {
      if (!dragging) return;
      dragging = false;
      var done = maxDx > 0 && dragX >= SLIDE_COMPLETE_FRACTION * maxDx;
      dragX = 0;
      resetThumb();
      if (done) fireStageAdvance();
    }
    $("trip-next-btn").addEventListener("pointerup", finishDrag);
    $("trip-next-btn").addEventListener("pointercancel", function () {
      dragging = false;
      dragX = 0;
      resetThumb();
    });
    $("trip-next-btn").addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        fireStageAdvance();
      }
    });
  }
  wireTripSlide();
  function advanceStage(current, extra, btn) {
    postTripEvent(current, extra)
      .then(function (res) {
        state.advancing = false;
        btn.disabled = false;
        if (!res.ok) {
          $("trip-error").textContent = (res.j && (res.j.error || res.j.message)) || "That step could not be saved. Please try again.";
          refreshGateNote();
          return;
        }
        if (current === "en_route") { startLocationSharing(); }
        if (current === "complete") { endTrip(); return; }
        state.stageIndex++;
        renderStages();
        /* "Head to pickup" and "Start trip" offer navigation straight
           to the pickup / drop-off; the other stages do not. The
           stage has already advanced, so dismissing the chooser is
           harmless. */
        maybeShowNavChooser(current);
      })
      .catch(function () {
        state.advancing = false;
        btn.disabled = false;
        $("trip-error").textContent = "Could not reach the service. Please try again.";
        refreshGateNote();
      });
  }
  /* Emergency-cancel reason step (owner rule 2026-11-18): inside
     2 hours the driver must pick a reason before cancelling. The
     reason is checked automatically by the server — no human
     review, and nothing about this flow is ever shown to the
     customer. */
  function showCancelReasonPanel() {
    hide($("trip-cancel-btn"));
    hide($("trip-cancel-note"));
    $("cancel-reason-error").textContent = "";
    show($("trip-cancel-reason-panel"));
  }
  function hideCancelReasonPanel() {
    hide($("trip-cancel-reason-panel"));
    var radios = document.querySelectorAll('input[name="cancel-reason"]');
    for (var i = 0; i < radios.length; i++) { radios[i].checked = false; }
    $("cancel-reason-detail").value = "";
    $("cancel-reason-error").textContent = "";
    show($("trip-cancel-btn"));
    show($("trip-cancel-note"));
    refreshCancelButton();
  }
  $("trip-cancel-btn").addEventListener("click", function () {
    if (!state.trip) return;
    /* Inside 2 hours: open the reason step instead of cancelling
       straight away. More than 2 hours out: the plain confirm, as
       before. */
    if (state.cancelLocked) { showCancelReasonPanel(); return; }
    if (!window.confirm("Cancel this job? The job goes to the next driver automatically.")) return;
    /* Only leave the trip screen when the server accepted the cancel.
       A rejected cancel (409) keeps the driver on the trip and shows
       the reason. */
    postTripEvent("cancel", {}).then(function (res) {
      if (res.ok) { endTrip(); return; }
      $("trip-error").textContent = (res.j && (res.j.error || res.j.message)) || "This job could not be cancelled.";
      refreshCancelButton();
    }).catch(function () {
      $("trip-error").textContent = "Could not reach the service. Please try again.";
    });
  });
  $("cancel-reason-back").addEventListener("click", function () {
    hideCancelReasonPanel();
  });
  $("cancel-reason-confirm").addEventListener("click", function () {
    if (!state.trip) return;
    var picked = null;
    var radios = document.querySelectorAll('input[name="cancel-reason"]');
    for (var i = 0; i < radios.length; i++) { if (radios[i].checked) { picked = radios[i].value; break; } }
    var detail = ($("cancel-reason-detail").value || "").trim();
    var errEl = $("cancel-reason-error");
    if (!picked) { errEl.textContent = "Please pick a reason."; return; }
    if (picked === "other" && !detail) { errEl.textContent = "Please say what happened."; return; }
    errEl.textContent = "";
    postTripEvent("cancel", { reason: picked, detail: detail }).then(function (res) {
      if (res.ok) {
        /* A fault judgment suspends the driver app for 48 hours:
           carry the end time into the home screen so the suspension
           banner shows at once. */
        var ec = res.j && res.j.emergency_cancel;
        if (ec && ec.suspended_until) {
          state.driver = state.driver || {};
          state.driver.suspended_until = ec.suspended_until;
        }
        hideCancelReasonPanel();
        endTrip();
        renderAvailability();
        return;
      }
      errEl.textContent = (res.j && (res.j.error || res.j.message)) || "This job could not be cancelled.";
    }).catch(function () {
      errEl.textContent = "Could not reach the service. Please try again.";
    });
  });
  $("trip-noshow-btn").addEventListener("click", function () {
    if (!state.trip) return;
    if (!window.confirm("Mark this ride as a customer no-show?")) return;
    postTripEvent("no_show", {}).then(function () { endTrip(); }).catch(function () { endTrip(); });
  });
  function endTrip() {
    stopLocationSharing();
    stopNoShowTimer();
    stopReminderPolling();
    stopChatPolling();
    hide($("namesign-overlay"));
    hideNavChooser();
    hide($("trip-reminder-banner"));
    hide($("trip-cancel-reason-panel"));
    var cancelRadios = document.querySelectorAll('input[name="cancel-reason"]');
    for (var ri = 0; ri < cancelRadios.length; ri++) { cancelRadios[ri].checked = false; }
    $("cancel-reason-detail").value = "";
    $("cancel-reason-error").textContent = "";
    state.reminderChimedBookingId = null;
    state.trip = null;
    state.stageIndex = 0;
    state.lastPosition = null;
    state.locationError = false;
    state.advancing = false;
    hide($("loc-note"));
    hide($("trip-gate-note"));
    hide($("trip-noshow-btn"));
    showScreen("home");
    refreshOffers();
  }

  /* ---------- Location sharing while heading to pickup ---------- */
  function startLocationSharing() {
    var note = $("loc-note");
    if (!("geolocation" in navigator)) {
      note.textContent = "Location sharing is not available on this device. The trip can continue without it.";
      show(note);
      return;
    }
    note.textContent = "Sharing your location while you head to pickup.";
    show(note);
    var send = function (pos) {
      if (!state.trip) return;
      state.lastPosition = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      state.locationError = false;
      refreshGateNote();
      fetch("/api/drivers/me/trip/" + encodeURIComponent(state.trip.id) + "/location", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
      }).catch(function () { /* a missed update is harmless; the next one follows */ });
    };
    var onErr = function () {
      state.locationError = true;
      refreshGateNote();
      note.textContent = "Location sharing is off. The trip can continue without it — the customer will not see live movement.";
    };
    try {
      state.watchId = navigator.geolocation.watchPosition(send, onErr, { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 });
    } catch (e) {
      onErr();
    }
  }
  function stopLocationSharing() {
    if (state.watchId !== null && "geolocation" in navigator) {
      try { navigator.geolocation.clearWatch(state.watchId); } catch (e) { /* ignore */ }
    }
    state.watchId = null;
  }

  /* ---------- Earnings ---------- */
  function fmtDay(isoDate) {
    /* Format a YYYY-MM-DD date without timezone shifting. */
    var parts = String(isoDate || "").split("-");
    if (parts.length !== 3) return String(isoDate || "");
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var m = parseInt(parts[1], 10);
    if (!m || m < 1 || m > 12) return String(isoDate);
    return months[m - 1] + " " + parseInt(parts[2], 10) + ", " + parts[0];
  }
  function renderPayoutWeeks(weeks) {
    var box = $("payout-weeks");
    if (!box) return;
    box.innerHTML = "";
    (weeks || []).forEach(function (w) {
      var paid = w.paid === true || w.status === "paid";
      var count = pickNumber(w, ["ride_count", "rides", "rideCount"]);
      var card = document.createElement("div");
      card.className = "pay-week";
      card.innerHTML =
        '<div class="pw-top"><div class="pw-range">' + esc(fmtDay(w.start) + " – " + fmtDay(w.end)) + "</div>" +
        '<span class="badge ' + (paid ? "done" : "todo") + '">' + (paid ? "Paid" : "Unpaid") + "</span></div>" +
        '<div class="pw-meta">Due ' + esc(fmtDay(w.due_date)) +
        (count !== null ? " · " + count + " ride(s)" : "") + "</div>";
      box.appendChild(card);
    });
  }
  function loadEarnings() {
    fetch("/api/drivers/me/earnings", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var weeks = j.weeks || j.pay_periods || j.payouts || [];
        renderPayoutWeeks(weeks);
        /* PAUSED (owner decision 2026-11-20): amounts are hidden, so
           there is nothing available to cash out. */
        state.unpaidCashout = 0;
        renderPayoutSetup();
        var list = Array.isArray(j) ? j : (j.earnings || j.rides || j.completed || []);
        var box = $("earnings-list");
        box.innerHTML = "";
        list.forEach(function (r) {
          var route = esc(r.route || "");
          if (!route) {
            route = esc(r.pickup || "");
            if (r.dropoff) route += " → " + esc(r.dropoff);
          }
          var meta = [r.date, r.time].filter(Boolean).join(" · ");
          var rcls = classLabelFor(r);
          if (rcls) meta += (meta ? " · " : "") + rcls;
          if (r.payout_status === "paid" || r.payout_paid === true) {
            meta += (meta ? " · " : "") + "Paid";
          } else if (r.payout_status === "unpaid" || r.payout_paid === false) {
            meta += (meta ? " · " : "") + "Unpaid";
          }
          var div = document.createElement("div");
          div.className = "earn-item";
          div.innerHTML = "<div><div class=\"r\">" + (route || "Ride") + "</div><div class=\"m\">" + esc(meta) + "</div></div>";
          box.appendChild(div);
        });
        /* PAUSED (owner decision 2026-11-20): amounts are hidden. */
        $("earnings-sum").textContent = "Amounts are hidden while prices are being updated.";
        if (!list.length) {
          show($("earnings-empty"));
        } else {
          hide($("earnings-empty"));
        }
      })
      .catch(function () { /* keep the previous view on a failed check */ });
  }

  /* ---------- Payout setup (Stripe Connect) ---------- */
  /* Weekly payout (free, due 7 days after the week starts) needs a
     bank account on file; instant cash-out needs a linked debit
     card. Bank details are entered in Stripe's hosted onboarding
     only — never in this app and never sent to Noel. PAUSED (owner
     decision 2026-11-20): instant cash-out is paused and no amounts
     are shown anywhere on this screen. */
  function renderPayoutSetup() {
    var statusEl = $("payout-setup-status");
    if (!statusEl) return;
    var s = state.payoutSetup;
    var bankEl = $("payout-bank-line");
    var weeklyNote = $("payout-weekly-note");
    var debitEl = $("payout-debit-line");
    var cashoutAmount = $("payout-cashout-amount");
    var cashoutBtn = $("payout-cashout-btn");
    var setupBtn = $("payout-setup-btn");
    if (!s) {
      statusEl.textContent = "Loading payout setup…";
      if (cashoutBtn) cashoutBtn.disabled = true;
      return;
    }
    if (s.bank_on_file && s.bank_masked) {
      bankEl.textContent = "Bank on file: " + s.bank_masked;
    } else {
      bankEl.textContent = "No bank account on file — weekly payouts need one";
    }
    if (s.payouts_enabled) {
      statusEl.textContent = "Weekly payouts are set up.";
      weeklyNote.textContent = "Your weekly payout is free and comes due 7 days after the week starts.";
    } else if (s.bank_on_file) {
      statusEl.textContent = "Bank on file. Finish setup to turn payouts on.";
      weeklyNote.textContent = "Weekly payout (free, due 7 days after the week starts) needs a bank account on file.";
    } else {
      statusEl.textContent = "Payouts are not set up yet.";
      weeklyNote.textContent = "Weekly payout (free, due 7 days after the week starts) needs a bank account on file.";
    }
    if (setupBtn) setupBtn.textContent = s.connect_account ? "Update payout setup" : "Set up payouts";
    var card = (s.debit_cards && s.debit_cards.length) ? s.debit_cards[0] : null;
    if (s.debit_card_linked && card) {
      var brand = card.brand ? String(card.brand).charAt(0).toUpperCase() + String(card.brand).slice(1) : "Debit card";
      debitEl.textContent = "Linked: " + brand + " •••• " + (card.last4 || "••••") +
        ((card.exp_month && card.exp_year) ? " (expires " + card.exp_month + "/" + card.exp_year + ")" : "");
    } else if (s.debit_card_linked) {
      debitEl.textContent = "Debit card linked.";
    } else {
      debitEl.textContent = "No debit card linked — link one to cash out instantly";
    }
    /* PAUSED (owner decision 2026-11-20): instant cash-out is paused
       and no amount is shown. */
    cashoutAmount.textContent = "Paused while prices are being updated.";
    if (cashoutBtn) {
      cashoutBtn.disabled = true;
    }
  }

  function loadPayoutSetup() {
    if (!$("payout-setup")) return;
    fetch("/api/drivers/me/payout-setup", { headers: authHeaders() })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.j) {
          $("payout-setup-status").textContent = (res.j && (res.j.error || res.j.message)) || "Payout setup could not be loaded.";
          return;
        }
        state.payoutSetup = res.j;
        if (res.j.instant_payout_fee_rate !== null && res.j.instant_payout_fee_rate !== undefined &&
            !isNaN(Number(res.j.instant_payout_fee_rate))) {
          state.payoutFeeRate = Number(res.j.instant_payout_fee_rate);
        }
        renderPayoutSetup();
      })
      .catch(function () {
        $("payout-setup-status").textContent = "Payout setup could not be loaded. Please try again.";
      });
  }

  /* "Set up payouts" and "Link debit card" both open Stripe's hosted
     onboarding, where the driver enters bank routing + account number
     (compulsory there) and links a debit card. A blank tab is opened
     in the tap itself so the pop-up blocker allows it; Stripe's URL
     goes in once the server returns it. */
  function startStripeOnboarding(endpoint, doneNote) {
    var err = $("payout-setup-error");
    var result = $("payout-cashout-result");
    err.textContent = "";
    result.textContent = "";
    var win = null;
    try { win = window.open("", "_blank"); } catch (e) { win = null; }
    fetch(endpoint, { method: "POST", headers: authHeaders() })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.j || !res.j.onboarding_url) {
          if (win) { try { win.close(); } catch (e) { /* ignore */ } }
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Payout setup could not be started. Please try again.";
          return;
        }
        var url = res.j.onboarding_url;
        if (win) {
          win.location = url;
        } else {
          var opened = null;
          try { opened = window.open(url, "_blank"); } catch (e) { opened = null; }
          if (!opened) {
            err.textContent = "Please allow pop-ups for this site, then try again.";
            return;
          }
        }
        result.textContent = doneNote;
      })
      .catch(function () {
        if (win) { try { win.close(); } catch (e) { /* ignore */ } }
        err.textContent = "Could not reach the payment service. Please try again.";
      });
  }

  $("payout-setup-btn").addEventListener("click", function () {
    startStripeOnboarding("/api/drivers/me/payout-setup",
      "Stripe onboarding opened in a new tab. Your bank details go to Stripe only — never to Noel. Come back here and reopen Earnings to see your updated setup.");
  });
  $("payout-link-card-btn").addEventListener("click", function () {
    startStripeOnboarding("/api/drivers/me/payout-setup/link-card",
      "Stripe opened in a new tab to link your debit card. Come back here and reopen Earnings to see it.");
  });

  /* Instant cash-out: confirms gross, 1.5% fee and net first, then
     POSTs. 409s (no unpaid earnings / no debit card linked /
     payouts not enabled yet) show the server's message verbatim. */
  $("payout-cashout-btn").addEventListener("click", function () {
    var err = $("payout-setup-error");
    var result = $("payout-cashout-result");
    err.textContent = "";
    result.textContent = "";
    /* PAUSED (owner decision 2026-11-20): instant cash-out is paused. */
    err.textContent = "Instant cash-out is paused while prices are being updated. Please check back soon.";
    return;
    var gross = state.unpaidCashout;
    if (!gross || gross <= 0) {
      err.textContent = "There are no unpaid earnings to cash out.";
      return;
    }
    if (!state.payoutSetup || !state.payoutSetup.debit_card_linked) {
      err.textContent = "Link a debit card first — without one, only the free weekly payout is available.";
      return;
    }
    var fee = Math.round(gross * state.payoutFeeRate * 100) / 100;
    var net = Math.round((gross - fee) * 100) / 100;
    var pct = (state.payoutFeeRate * 100).toFixed(1).replace(/\.0$/, "");
    if (!window.confirm("Cash out " + money(gross) + " now?\nFee (" + pct + "%): " + money(fee) + "\nYou receive: " + money(net))) return;
    var btn = $("payout-cashout-btn");
    btn.disabled = true;
    fetch("/api/drivers/me/instant-payout", { method: "POST", headers: authHeaders() })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok || !res.j || !res.j.instant_payout) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Instant payout could not be completed. Please try again.";
          renderPayoutSetup();
          return;
        }
        var p = res.j.instant_payout;
        var received = (res.j.driver_receives !== null && res.j.driver_receives !== undefined) ? res.j.driver_receives : p.net;
        result.textContent = "Cashed out " + money(p.amount !== undefined ? p.amount : gross) +
          ". Fee: " + money(p.fee !== undefined ? p.fee : fee) +
          ". You receive: " + money(received) + ".";
        loadEarnings();
        loadPayoutSetup();
      })
      .catch(function () {
        btn.disabled = false;
        err.textContent = "Could not reach the payment service. Please try again.";
        renderPayoutSetup();
      });
  });

  /* ---------- Tax info (display only — no form to fill in) ---------- */
  function loadTaxInfo() {
    fetch("/api/drivers/me/tax-info", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        /* PAUSED (owner decision 2026-11-20): amounts are hidden. */
        $("tax-earnings-2026").textContent = "Amounts are hidden while prices are being updated.";
        var rides = pickNumber(j, ["completed_rides_year", "ride_count"]);
        $("tax-rides-2026").textContent = rides !== null
          ? rides + (rides === 1 ? " completed ride" : " completed rides") + " in 2026"
          : "";
      })
      .catch(function () { /* keep the previous view on a failed check */ });
  }

  /* ---------- Documents ---------- */
  function docIsComplete(value) {
    if (value === true) return true;
    if (!value) return false;
    if (typeof value === "string") {
      var v = value.toLowerCase();
      if (v === "completed" || v === "complete" || v === "approved" || v === "verified") return true;
      if (v.indexOf("http") === 0 || v.indexOf("/") === 0) return true;
      return false;
    }
    if (typeof value === "object") {
      var st = String(value.status || value.state || "").toLowerCase();
      if (st === "completed" || st === "complete" || st === "approved" || st === "verified") return true;
      if (st === "missing" || st === "pending" || st === "remaining" || st === "incomplete") return false;
      if (value.url || value.path || value.file || value.document_id || value.id) return true;
    }
    return false;
  }
  function renderDocuments() {
    var box = $("documents-list");
    box.innerHTML = "";
    /* The API returns document statuses as `docs` keyed by document
       type (e.g. dmv_license: "completed") — exactly the types the
       driver's state requires, so only those rows are shown, in
       display order. Drivers registered before the state selector
       read as New York and see the original 7 rows. */
    var docs = (state.driver && (state.driver.docs || state.driver.documents)) || {};
    var byKey = {};
    if (Array.isArray(docs)) {
      docs.forEach(function (d) {
        var key = d.key || d.field || d.name || d.document || "";
        byKey[key] = d;
      });
    } else if (typeof docs === "object") {
      byKey = docs;
    }
    DOC_TYPE_ORDER.forEach(function (docType) {
      if (byKey[docType] === undefined) return;
      var done = docIsComplete(byKey[docType]);
      var row = document.createElement("div");
      row.className = "doc-status";
      row.innerHTML = '<span class="name">' + esc(DOC_TYPE_LABELS[docType] || docType) + "</span>" +
        '<span class="badge ' + (done ? "done" : "todo") + '">' + (done ? "Completed" : "Items remaining") + "</span>";
      box.appendChild(row);
      /* Expiry (owner decision 2026-11-19): show the stored expiry
         date, and a re-upload box when the document is expired or
         expiring within 10 days — the renewal path that lifts the
         registration pause automatically. */
      var expiries = (state.driver && state.driver.doc_expiries) || {};
      var expDate = expiries[docType];
      var expiredList = (state.driver && state.driver.expired_docs) || [];
      var expiringList = (state.driver && state.driver.expiring_docs) || [];
      var isExpired = expiredList.some(function (x) { return x.doc_type === docType; });
      var expiring = null;
      expiringList.forEach(function (x) { if (x.doc_type === docType) expiring = x; });
      if (done && expDate) {
        var expEl = document.createElement("div");
        expEl.className = "doc-expiry" + (isExpired ? " expired" : (expiring ? " soon" : ""));
        expEl.textContent = isExpired ? ("Expired " + expDate)
          : (expiring ? ("Expires " + expDate + " — in " + expiring.days_left + (expiring.days_left === 1 ? " day" : " days"))
                      : ("Expires " + expDate));
        box.appendChild(expEl);
      }
      if (done && (isExpired || expiring)) {
        var hasExpiry = ((state.driver && state.driver.expiry_doc_types) || []).indexOf(docType) !== -1;
        var up = document.createElement("div");
        up.className = "doc-reupload";
        var upHtml = '<label class="doc-reupload-label">Upload a new, valid document</label>' +
          '<input type="file" class="doc-reupload-file" accept="image/*,.pdf">';
        if (hasExpiry) {
          upHtml += '<label class="doc-reupload-label">Expiry date — as printed on the document</label>' +
            '<input type="date" class="doc-reupload-expiry">';
        }
        upHtml += '<button type="button" class="btn-primary doc-reupload-btn">Upload new document</button>' +
          '<div class="doc-reupload-error" role="alert"></div>';
        up.innerHTML = upHtml;
        up.querySelector(".doc-reupload-btn").addEventListener("click", function () {
          uploadDocReplacement(docType, hasExpiry, up);
        });
        box.appendChild(up);
      }
    });
  }

  /* Re-upload one document (owner decision 2026-11-19): the renewal
     path for an expired or expiring document. Same server checks as
     registration — duplicate photo, photo sanity, valid future
     expiry — and a fresh expiry lifts the registration pause
     automatically, with no owner action. */
  function uploadDocReplacement(docType, hasExpiry, box) {
    var fileInput = box.querySelector(".doc-reupload-file");
    var dateInput = box.querySelector(".doc-reupload-expiry");
    var errEl = box.querySelector(".doc-reupload-error");
    var btn = box.querySelector(".doc-reupload-btn");
    errEl.textContent = "";
    var file = fileInput && fileInput.files && fileInput.files[0];
    if (!file) { errEl.textContent = "Please choose a document photo to upload."; return; }
    var fd = new FormData();
    fd.append("doc_type", docType);
    fd.append("document", file);
    if (hasExpiry) {
      if (!dateInput || !dateInput.value) {
        errEl.textContent = "Please enter the expiry date as printed on the document.";
        return;
      }
      fd.append("expiry_" + docType, dateInput.value);
    }
    btn.disabled = true;
    btn.textContent = "Uploading…";
    fetch("/api/drivers/me/documents", { method: "POST", headers: authHeaders(), body: fd })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          errEl.textContent = (res.j && res.j.error) || "Upload failed — please try again.";
          btn.disabled = false;
          btn.textContent = "Upload new document";
          return;
        }
        refreshDriverState().then(function () { renderDocuments(); });
      })
      .catch(function () {
        errEl.textContent = "Upload failed — please try again.";
        btn.disabled = false;
        btn.textContent = "Upload new document";
      });
  }

  /* ---------- Profile ---------- */
  function renderProfile() {
    var d = state.driver || {};
    var carBits = [d.car_year, d.car_model, d.car_colour].filter(Boolean).join(" · ");
    var bank = d.bank_account_number || d.bank_account || d.account_number || d.masked_account || d.bank_masked || "";
    var bankText = bank ? maskBank(String(bank).indexOf("•") !== -1 || String(bank).indexOf("*") !== -1 ? bank.replace(/[^0-9]/g, "").slice(-4) : bank) : "Saved";
    if (String(bank).indexOf("•") !== -1 || String(bank).indexOf("*") !== -1) {
      bankText = String(bank);
    }
    var photo = d.profile_photo_url || d.photo_url || d.profile_photo || "";
    var html = "";
    if (photo && typeof photo === "string" && photo.indexOf("http") === 0) {
      html += '<img src="' + esc(photo) + '" alt="Profile photo">';
    }
    html += '<div class="profile-row"><span class="k">Name</span><span>' + esc(d.name || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Phone</span><span>' + esc(d.phone || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Email</span><span>' + esc(d.email || "—") + "</span></div>" +
      (d.state ? '<div class="profile-row"><span class="k">State</span><span>' + esc(d.state) + "</span></div>" : "") +
      (d.city ? '<div class="profile-row"><span class="k">City</span><span>' + esc(d.city) + "</span></div>" : "") +
      '<div class="profile-row"><span class="k">Car</span><span>' + esc(carBits || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Vehicle class</span><span>' + esc(classLabelFor(d) || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Plate</span><span>' + esc(d.plate || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Bank account</span><span>' + esc(bankText) + "</span></div>";
    $("profile-card").innerHTML = html;
  }
  /* ---------- Driver referral ---------- */
  /* Owner decision 2026-11-18: the driver referral is a shareable
     LINK, not a code number — same pattern as the customer referral
     link. The driver taps "Refer a Friend" to reveal his link, then
     Copy or the native Share sheet to send it himself (WhatsApp,
     message, etc.) — the system sends nothing to friends. A friend
     who clicks the link lands straight in driver registration (see
     boot above). Below the link, the driver sees his own referral
     earnings only: total earned and one row per referred driver
     (jobs counted out of the first 15). */
  function driverReferralLinkFor(code) {
    return window.location.origin + "/driver?ref=" + encodeURIComponent(code);
  }
  function copyDriverReferralLink(text, btn) {
    var label = btn ? btn.textContent : "";
    function done() {
      if (!btn) return;
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = label; }, 2000);
    }
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (e) { /* clipboard unavailable */ }
      document.body.removeChild(ta);
      done();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else {
      fallback();
    }
  }
  function renderDriverReferralEarnings(j) {
    var box = $("driver-referral-earnings");
    if (!box) return;
    var maxJobs = pickNumber(j, ["max_jobs_per_driver"]) || 15;
    /* PAUSED (owner decision 2026-11-20): no referral amounts shown. */
    var html = '<p class="form-note">Referral amounts are hidden while prices are being updated.</p>';
    var friends = (j && j.referred_drivers) || [];
    if (!friends.length) {
      html += '<p class="form-note">No friends referred yet. Share your link to get started.</p>';
    } else {
      friends.forEach(function (f) {
        var counted = pickNumber(f, ["jobs_counted"]);
        html += '<div class="referral-earn-row"><span>' + esc(f.name || "Driver") + "</span><span>" +
          esc(String(counted !== null ? counted : 0)) + " of " + esc(String(maxJobs)) + " rides</span></div>";
      });
    }
    box.innerHTML = html;
  }
  function loadDriverReferral() {
    var box = $("driver-referral-box");
    if (!box) return;
    fetch("/api/drivers/me/referral", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var code = j && j.referral_code;
        var revealBtn = $("driver-referral-show-btn");
        if (!code) {
          hide(revealBtn);
          hide($("driver-referral-link-line"));
          hide($("driver-referral-actions"));
          return;
        }
        var link = driverReferralLinkFor(code);
        var anchor = $("driver-referral-link-anchor");
        anchor.href = link;
        anchor.textContent = link;
        var copyBtn = $("driver-referral-copy-btn");
        copyBtn.onclick = function () { copyDriverReferralLink(link, copyBtn); };
        var shareBtn = $("driver-referral-share-btn");
        if (navigator.share) {
          show(shareBtn);
          shareBtn.onclick = function () {
            navigator.share({ title: "Noel Chauffer", url: link }).catch(function () {});
          };
        } else {
          hide(shareBtn);
        }
        revealBtn.onclick = function () {
          show($("driver-referral-link-line"));
          show($("driver-referral-actions"));
          hide(revealBtn);
        };
        show(revealBtn);
        renderDriverReferralEarnings(j);
      })
      .catch(function () { /* keep the previous view on a failed check */ });
  }
  $("reset-driver-btn").addEventListener("click", function () {
    if (!window.confirm("Sign out this driver on this device and show the sign-in screen?")) return;
    stopLocationSharing();
    clearToken();
    /* A different driver on this device must hear fresh offers. */
    clearSeenOfferIds();
    state.driver = null;
    state.trip = null;
    window.location.reload();
  });

  /* ---------- Car model dropdown (registration) ---------- */
  /* Searchable dropdown fed by GET /api/car-models — the same single
     list the server validates against. Type to filter; tap a
     suggestion to choose it. Free text is not accepted: the chosen
     value must match a list entry exactly. The year select is filled
     from the same response (2022 through current year + 1). */
  var carModels = [];
  var carListLoaded = false;

  function fillYearSelect(minYear, maxYear) {
    var sel = $("reg-car-year");
    sel.innerHTML = '<option value="">Select year</option>';
    for (var y = maxYear; y >= minYear; y--) {
      var opt = document.createElement("option");
      opt.value = String(y);
      opt.textContent = String(y);
      sel.appendChild(opt);
    }
  }

  /* Show/hide password (eye) toggle: one button inside each
     password field (sign-in, registration, reset). Tapping it
     switches the field between dots and plain text and flips the
     label between Show and Hide. It never changes the value, the
     validation, or what the form submits. */
  function initPasswordEyes() {
    var buttons = document.querySelectorAll(".password-eye");
    Array.prototype.forEach.call(buttons, function (btn) {
      btn.addEventListener("click", function () {
        var input = $(btn.getAttribute("data-for"));
        if (!input) { return; }
        var showing = input.type === "text";
        input.type = showing ? "password" : "text";
        btn.textContent = showing ? "Show" : "Hide";
        btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      });
    });
  }

  function initCarModelDropdown() {
    var input = $("reg-car-model");
    var list = $("car-model-list");
    var note = $("car-model-note");
    var activeIndex = -1;
    var items = [];

    function closeList() {
      hide(list);
      list.innerHTML = "";
      items = [];
      activeIndex = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    function paintActive() {
      var btns = list.querySelectorAll("button");
      btns.forEach(function (b, i) {
        b.classList.toggle("active", i === activeIndex);
        b.setAttribute("aria-selected", i === activeIndex ? "true" : "false");
      });
      if (activeIndex >= 0 && btns[activeIndex]) {
        input.setAttribute("aria-activedescendant", btns[activeIndex].id);
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }
    function choose(name) {
      input.value = name;
      closeList();
      input.focus();
    }
    function render(matches) {
      items = matches;
      activeIndex = -1;
      list.innerHTML = "";
      if (!matches.length) { closeList(); return; }
      matches.forEach(function (name, idx) {
        var li = document.createElement("li");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.setAttribute("role", "option");
        btn.setAttribute("aria-selected", "false");
        btn.id = "car-model-list-opt-" + idx;
        btn.textContent = name;
        /* mousedown fires before the input loses focus, so a tap or
           click always lands on the suggestion. */
        btn.addEventListener("mousedown", function (e) {
          e.preventDefault();
          choose(name);
        });
        li.appendChild(btn);
        list.appendChild(li);
      });
      show(list);
      input.setAttribute("aria-expanded", "true");
    }
    function filter() {
      var q = input.value.trim().toLowerCase();
      var matches = carModels.filter(function (name) {
        return !q || name.toLowerCase().indexOf(q) !== -1;
      }).slice(0, 8);
      render(matches);
    }
    input.addEventListener("input", filter);
    input.addEventListener("focus", filter);
    input.addEventListener("blur", function () {
      /* A tap on a suggestion fires mousedown first; the short delay
         keeps that working on touch screens. */
      setTimeout(closeList, 150);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (!items.length) return;
        e.preventDefault();
        activeIndex = e.key === "ArrowDown"
          ? (activeIndex + 1) % items.length
          : (activeIndex - 1 + items.length) % items.length;
        paintActive();
      } else if (e.key === "Enter") {
        if (activeIndex >= 0 && items[activeIndex]) {
          e.preventDefault();
          choose(items[activeIndex]);
        }
      } else if (e.key === "Escape") {
        closeList();
      }
    });

    /* The Model 3 exception is only visible to the two allowed
       drivers (owner decision 2026-11-19): the list is fetched with
       the email typed in the registration form, so other drivers
       never even see Model 3. Re-fetch when the email changes; if
       the chosen model just left the list, clear it. */
    function loadCarModels() {
      var email = $("reg-email").value.trim();
      var url = email
        ? "/api/car-models?email=" + encodeURIComponent(email)
        : "/api/car-models";
      fetch(url)
        .then(function (r) { return r.json(); })
        .then(function (j) {
          carModels = j.models || [];
          carListLoaded = carModels.length > 0;
          fillYearSelect(j.min_year || 2022, j.max_year || new Date().getFullYear() + 1);
          if (!carListLoaded) { throw new Error("empty list"); }
          if (input.value && carModels.indexOf(input.value.trim()) === -1) {
            input.value = "";
          }
        })
        .catch(function () {
          note.textContent = "The car list could not be loaded. Please check your connection and reload this page.";
          input.disabled = true;
          $("register-submit").disabled = true;
        });
    }
    loadCarModels();
    $("reg-email").addEventListener("change", loadCarModels);
  }

  /* ---------- State dropdown + per-state documents (registration) ---------- */
  /* Searchable dropdown fed by GET /api/states — the same single
     mapping the server validates against. States only, alphabetical,
     type to filter: typing a letter shows every state starting with
     it (N shows Nebraska, Nevada, New Hampshire, New Jersey, New
     Mexico, New York, North Carolina, North Dakota), and typing more
     letters narrows the list. Free text is not accepted: the chosen
     value must match a list entry exactly. The chosen state decides
     which document items the form shows, because the compulsory list
     differs by state (New York keeps its 7; New Jersey has its own
     verified list; every other state uses the generic base list) —
     unless the chosen city has a verified city-specific list
     (Dallas today), which overrides its state list. The same
     payload feeds the city picker right after the state picker:
     cities of the chosen state, alphabetical, type to filter, with
     an "Other city" fallback for unlisted towns. */
  var stateNames = [];
  var stateListLoaded = false;
  var stateRequirements = null;
  var stateDocuments = null;
  /* City picker data, from the same /api/states payload: city names
     per state, and the verified city-specific lists that override
     their state list. */
  var cityNamesByState = null;
  var cityRequirements = null;
  var cityListLoaded = false;

  /* City names for a state, in picker order (alphabetical, "Other
     city" last). Empty when the data has not loaded or the state is
     unknown. */
  function citiesForState(stateName) {
    if (!cityNamesByState || !cityNamesByState[stateName]) return [];
    return cityNamesByState[stateName];
  }

  /* The requirement in force for a state + city: a city with a
     verified city-specific list overrides its state list; every
     other city — including "Other city" and no city yet — uses the
     state list unchanged. Null when no valid state is chosen. */
  function effectiveRequirement(stateName, cityName) {
    if (!stateRequirements || !stateRequirements[stateName]) return null;
    if (cityName && cityRequirements && cityRequirements[stateName] &&
        cityRequirements[stateName][cityName]) {
      return cityRequirements[stateName][cityName];
    }
    return stateRequirements[stateName];
  }

  /* Multipart field names the chosen state + city list requires, in
     form order. Empty when no valid state is chosen (or the list has
     not loaded yet), which blocks the submit handler. */
  function requiredFileFields(stateName, cityName) {
    var req = effectiveRequirement(stateName, cityName);
    if (!req) return [];
    var fields = [];
    (req.docs || []).forEach(function (docType) {
      var field = FIELD_FOR_DOC_TYPE[docType];
      if (field) fields.push(field);
    });
    return fields;
  }

  /* Build the upload item for a document type that has no static form
     item (states other than New York). Built once, then shown and
     hidden as the driver changes state, so a chosen file survives a
     state switch. Labels and hints come from the states endpoint. */
  function ensureDocItem(docType) {
    var spec = stateDocuments && stateDocuments[docType];
    if (!spec) return null;
    var field = spec.field;
    var item = $("doc-item-" + field);
    if (item) return item;
    item = document.createElement("div");
    item.className = "doc-item";
    item.id = "doc-item-" + field;
    var nameEl = document.createElement("div");
    nameEl.className = "doc-name";
    nameEl.textContent = spec.label;
    var hintEl = document.createElement("div");
    hintEl.className = "doc-hint";
    hintEl.textContent = spec.hint;
    var input = document.createElement("input");
    input.type = "file";
    input.id = "file-" + field;
    input.accept = spec.accept || "image/*";
    var preview = document.createElement("div");
    preview.className = "doc-preview";
    preview.id = "preview-" + field;
    var errorEl = document.createElement("div");
    errorEl.className = "doc-error";
    errorEl.id = "doc-error-" + field;
    item.appendChild(nameEl);
    item.appendChild(hintEl);
    item.appendChild(input);
    /* Expiry date for documents that have one (owner decision
       2026-11-19): the driver types the date printed on the
       document; the server rejects a past date. */
    if (spec.has_expiry) {
      var expLabel = document.createElement("label");
      expLabel.className = "expiry-label";
      expLabel.setAttribute("for", "expiry-" + field);
      expLabel.textContent = "Expiry date — as printed on the document";
      var expInput = document.createElement("input");
      expInput.type = "date";
      expInput.id = "expiry-" + field;
      expInput.className = "expiry-input";
      item.appendChild(expLabel);
      item.appendChild(expInput);
    }
    item.appendChild(preview);
    item.appendChild(errorEl);
    $("doc-items-extra").appendChild(item);
    bindFilePreview(field);
    return item;
  }

  /* Show exactly the chosen state + city document items, in the
     effective list's order, and update the required-items note. A
     city with a verified city-specific list overrides its state
     list; every other city shows the state list. With no state
     chosen, every item stays hidden behind the choose-your-state
     note. */
  function renderDocsForState(stateName, cityName) {
    var req = effectiveRequirement(stateName, cityName);
    var required = req ? (req.docs || []) : [];
    var note = $("docs-required-note");
    var localNote = $("docs-local-note");
    STATIC_DOC_TYPES.forEach(function (docType) {
      var item = $("doc-item-" + FIELD_FOR_DOC_TYPE[docType]);
      if (!item) return;
      if (required.indexOf(docType) !== -1) show(item); else hide(item);
    });
    DOC_TYPE_ORDER.forEach(function (docType) {
      if (STATIC_DOC_TYPES.indexOf(docType) !== -1) return;
      if (required.indexOf(docType) !== -1) {
        var built = ensureDocItem(docType);
        if (built) show(built);
      } else {
        var existing = $("doc-item-" + FIELD_FOR_DOC_TYPE[docType]);
        if (existing) hide(existing);
      }
    });
    if (!req) {
      note.textContent = "Choose your state above — the documents you need depend on your state.";
      hide(localNote);
      return;
    }
    note.textContent = "All items are required — registration cannot be completed until every document is uploaded.";
    if (req.local_note) show(localNote); else hide(localNote);
  }

  /* Keep the city picker in step with the chosen state: the city
     list belongs to the state, so a state change resets a city that
     does not belong to the new state, and no valid state means no
     city picker yet. */
  function refreshCityForState(stateName) {
    var input = $("reg-city");
    var valid = !!(stateRequirements && stateRequirements[stateName]);
    if (!valid || !cityListLoaded) {
      input.value = "";
      input.disabled = true;
      input.placeholder = "Choose your state first…";
      return;
    }
    input.disabled = false;
    input.placeholder = "Start typing your city…";
    var current = input.value.trim();
    if (current && citiesForState(stateName).indexOf(current) === -1) {
      input.value = "";
    }
  }

  function initStateDropdown() {
    var input = $("reg-state");
    var list = $("state-list");
    var note = $("state-note");
    var activeIndex = -1;
    var items = [];

    /* No state chosen yet: hide the document items until one is. */
    renderDocsForState(null);

    function closeList() {
      hide(list);
      list.innerHTML = "";
      items = [];
      activeIndex = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    function paintActive() {
      var btns = list.querySelectorAll("button");
      btns.forEach(function (b, i) {
        b.classList.toggle("active", i === activeIndex);
        b.setAttribute("aria-selected", i === activeIndex ? "true" : "false");
      });
      if (activeIndex >= 0 && btns[activeIndex]) {
        input.setAttribute("aria-activedescendant", btns[activeIndex].id);
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }
    function choose(name) {
      input.value = name;
      closeList();
      refreshCityForState(name);
      renderDocsForState(name, $("reg-city").value.trim());
      input.focus();
    }
    function render(matches) {
      items = matches;
      activeIndex = -1;
      list.innerHTML = "";
      if (!matches.length) { closeList(); return; }
      matches.forEach(function (name, idx) {
        var li = document.createElement("li");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.setAttribute("role", "option");
        btn.setAttribute("aria-selected", "false");
        btn.id = "state-list-opt-" + idx;
        btn.textContent = name;
        /* mousedown fires before the input loses focus, so a tap or
           click always lands on the suggestion. */
        btn.addEventListener("mousedown", function (e) {
          e.preventDefault();
          choose(name);
        });
        li.appendChild(btn);
        list.appendChild(li);
      });
      show(list);
      input.setAttribute("aria-expanded", "true");
    }
    function filter() {
      var q = input.value.trim().toLowerCase();
      /* Prefix match, list order kept: one letter shows every state
         starting with it; more letters narrow the list. */
      var matches = stateNames.filter(function (name) {
        return !q || name.toLowerCase().indexOf(q) === 0;
      });
      render(matches);
      /* Typing a full state name shows its documents at once, and
         opens the city picker for that state. */
      var exact = input.value.trim();
      refreshCityForState(exact);
      if (stateRequirements && stateRequirements[exact]) {
        renderDocsForState(exact, $("reg-city").value.trim());
      } else if (!exact) {
        renderDocsForState(null);
      }
    }
    input.addEventListener("input", filter);
    input.addEventListener("focus", filter);
    input.addEventListener("blur", function () {
      /* A tap on a suggestion fires mousedown first; the short delay
         keeps that working on touch screens. */
      setTimeout(closeList, 150);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (!items.length) return;
        e.preventDefault();
        activeIndex = e.key === "ArrowDown"
          ? (activeIndex + 1) % items.length
          : (activeIndex - 1 + items.length) % items.length;
        paintActive();
      } else if (e.key === "Enter") {
        if (activeIndex >= 0 && items[activeIndex]) {
          e.preventDefault();
          choose(items[activeIndex]);
        }
      } else if (e.key === "Escape") {
        closeList();
      }
    });

    fetch("/api/states")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        stateNames = j.states || [];
        stateRequirements = j.requirements || null;
        stateDocuments = j.documents || null;
        stateListLoaded = stateNames.length > 0 && !!stateRequirements;
        if (!stateListLoaded) { throw new Error("empty list"); }
        cityNamesByState = j.cities || null;
        cityRequirements = j.city_requirements || {};
        cityListLoaded = !!cityNamesByState &&
          Object.keys(cityNamesByState).length > 0;
        refreshCityForState($("reg-state").value.trim());
      })
      .catch(function () {
        note.textContent = "The state list could not be loaded. Please check your connection and reload this page.";
        input.disabled = true;
        $("register-submit").disabled = true;
      });
  }

  /* City picker, Uber-style: the same searchable-dropdown pattern as
     the state picker, fed by the same /api/states payload. Cities of
     the chosen state only, alphabetical, type to filter: typing a
     letter shows every city starting with it, more letters narrow
     the list. The list ends with "Other city" for drivers in
     unlisted towns. Free text is not accepted. Picking a city with
     a verified city-specific list (Dallas) swaps the document items
     to that city's list; every other city keeps the state list. */
  function initCityDropdown() {
    var input = $("reg-city");
    var list = $("city-list");
    var activeIndex = -1;
    var items = [];

    function currentState() { return $("reg-state").value.trim(); }
    function closeList() {
      hide(list);
      list.innerHTML = "";
      items = [];
      activeIndex = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    function paintActive() {
      var btns = list.querySelectorAll("button");
      btns.forEach(function (b, i) {
        b.classList.toggle("active", i === activeIndex);
        b.setAttribute("aria-selected", i === activeIndex ? "true" : "false");
      });
      if (activeIndex >= 0 && btns[activeIndex]) {
        input.setAttribute("aria-activedescendant", btns[activeIndex].id);
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }
    function choose(name) {
      input.value = name;
      closeList();
      renderDocsForState(currentState(), name);
      input.focus();
    }
    function render(matches) {
      items = matches;
      activeIndex = -1;
      list.innerHTML = "";
      if (!matches.length) { closeList(); return; }
      matches.forEach(function (name, idx) {
        var li = document.createElement("li");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.setAttribute("role", "option");
        btn.setAttribute("aria-selected", "false");
        btn.id = "city-list-opt-" + idx;
        btn.textContent = name;
        /* mousedown fires before the input loses focus, so a tap or
           click always lands on the suggestion. */
        btn.addEventListener("mousedown", function (e) {
          e.preventDefault();
          choose(name);
        });
        li.appendChild(btn);
        list.appendChild(li);
      });
      show(list);
      input.setAttribute("aria-expanded", "true");
    }
    function filter() {
      var q = input.value.trim().toLowerCase();
      /* Prefix match, list order kept: one letter shows every city
         starting with it; more letters narrow the list. */
      var matches = citiesForState(currentState()).filter(function (name) {
        return !q || name.toLowerCase().indexOf(q) === 0;
      });
      render(matches);
      /* Typing a full city name swaps the documents at once when the
         city has its own list. */
      var exact = input.value.trim();
      if (citiesForState(currentState()).indexOf(exact) !== -1) {
        renderDocsForState(currentState(), exact);
      }
    }
    input.addEventListener("input", filter);
    input.addEventListener("focus", filter);
    input.addEventListener("blur", function () {
      /* A tap on a suggestion fires mousedown first; the short delay
         keeps that working on touch screens. */
      setTimeout(closeList, 150);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (!items.length) return;
        e.preventDefault();
        activeIndex = e.key === "ArrowDown"
          ? (activeIndex + 1) % items.length
          : (activeIndex - 1 + items.length) % items.length;
        paintActive();
      } else if (e.key === "Enter") {
        if (activeIndex >= 0 && items[activeIndex]) {
          e.preventDefault();
          choose(items[activeIndex]);
        }
      } else if (e.key === "Escape") {
        closeList();
      }
    });
  }

  initPasswordEyes();
  initCarModelDropdown();
  initStateDropdown();
  initCityDropdown();
  boot();
})();
