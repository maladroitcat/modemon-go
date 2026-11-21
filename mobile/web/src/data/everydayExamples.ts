export type EverydayExample = {
  title: string;
  description: string;
  illustrative: boolean;
};
export type EverydayExamples = Record<string, EverydayExample[]>;

// Authored by stable species ID, outside canonical content and quiz inputs.
// All scenarios below are hypothetical, including those naming local places.
const examples: Record<string, [string, string][]> = {
  anomaly_base: [
    ["A surprising energy bill", "A home energy tool could flag electricity use that differs sharply from the household’s usual pattern."],
    ["Unusual website activity", "A small business could compare daily visits with its normal range and flag a sudden change for review."],
  ],
  anomaly_fraud: [
    ["Card payment review", "A payment tool could flag a purchase that differs from an account’s usual spending, so a person can check it."],
    ["Suspicious online orders", "A shop could use order and account patterns to prioritize potentially fraudulent purchases for review."],
  ],
  anomaly_machine: [
    ["A noisy elevator motor", "A maintenance tool could spot unusual vibration or heat before a technician checks the equipment."],
    ["Refrigerator maintenance", "A restaurant could flag temperature patterns that differ from a refrigerator’s normal operation."],
  ],
  anomaly_network: [
    ["Unexpected sign-ins", "A university security team could flag login patterns that differ from an account’s usual activity."],
    ["An unusual data transfer", "A business could compare network traffic with normal patterns and alert staff to investigate a large transfer."],
  ],
  anomaly_vitals: [
    ["Heart-rate changes", "A monitoring tool could flag a sustained heart-rate pattern outside a person’s usual range for clinical review."],
    ["Recovery monitoring", "A care team could review alerts about unusual trends across several vital signs; an alert would not itself be a diagnosis."],
  ],
  detector_base: [
    ["Finding objects in photos", "A photo tool could label bicycles or dogs and mark where they appear in a picture."],
    ["Sorting recycling images", "A camera system could locate cans and bottles in images to support sorting."],
  ],
  detector_defect: [
    ["Checking a package", "A production camera could flag a torn label or damaged box for a worker to inspect."],
    ["Bakery quality checks", "A bakery could compare product photos to spot misshapen items before packaging them."],
  ],
  detector_disease: [
    ["Reviewing an X-ray", "An imaging tool could highlight a suspicious area for a radiologist to examine, rather than make a diagnosis on its own."],
    ["Measuring tissue", "A pathology image tool could outline tissue regions so specialists can review their size and appearance."],
  ],
  detector_pedestrian: [
    ["Crosswalk observation", "A street-camera tool could locate people in video frames to help study a busy crossing in Durham."],
    ["Driver assistance", "A vehicle camera could locate pedestrians and vehicles to support a warning system, while still missing some hazards."],
  ],
  extractor_archive: [
    ["Reading an old letter", "A transcription tool could turn a scanned handwritten letter into searchable text for a family-history project."],
    ["Digitizing a Durham archive", "An archive project could transcribe old handwritten registers, with people checking faded or ambiguous words."],
  ],
  extractor_base: [
    ["Organizing receipts", "A document tool could pull the merchant, date and total from receipt images into a table."],
    ["Sorting application forms", "A tool could extract names and contact fields from scanned forms for staff to verify."],
  ],
  extractor_government: [
    ["Permit intake", "A public-service office could extract addresses and dates from permit forms to reduce manual retyping."],
    ["Handwritten applications", "A civic office could turn handwritten application fields into draft electronic records for staff review."],
  ],
  extractor_history: [
    ["Studying neighborhood change", "Students could examine recurring themes across historical housing documents to guide questions about redlining."],
    ["Comparing old newspapers", "A history class could identify recurring names and relationships across articles, then check the original sources."],
  ],
  extractor_medical: [
    ["Medication lists", "A clinical text tool could pull medication names from notes into a draft list for a care team to verify."],
    ["Finding procedure dates", "A records tool could extract procedure names and dates from reports without deciding which treatment a patient needs."],
  ],
  extractor_research: [
    ["Comparing studies", "A student could extract study populations and reported measurements from papers into a review table."],
    ["Mapping research concepts", "A university team could pull named materials and their relationships from reports to help organize a literature review."],
  ],
  extractor_specimen: [
    ["Reading specimen labels", "A collection tool could transcribe handwritten fish labels into draft electronic specimen records."],
    ["Searching field notebooks", "A museum volunteer could turn handwritten specimen notes into searchable text while checking uncertain dates and places."],
  ],
  forecast_base: [
    ["Planning a café’s week", "A Durham café could estimate next week’s orders from past sales, weather and calendar patterns."],
    ["Predicting service requests", "A help desk could forecast tomorrow’s request volume to plan its capacity."],
  ],
  forecast_crowd: [
    ["A concert evening", "A Raleigh venue could estimate attendance from ticket sales, past events and weather to plan services."],
    ["Museum visits", "A Durham museum could forecast visitor volume during a school holiday; the estimate would describe a crowd, not identify visitors."],
  ],
  forecast_patient: [
    ["Planning clinic capacity", "A clinic could forecast the number of visits next week from seasonal and historical patterns."],
    ["Estimating bed demand", "A hospital could estimate future bed demand to support planning, without predicting a particular person’s outcome."],
  ],
  forecast_stock: [
    ["Ordering groceries", "A neighborhood shop could estimate how many cartons of milk it will sell before placing its next order."],
    ["Preparing for a promotion", "A store could use past sales and planned discounts to forecast how many units shoppers may want."],
  ],
  forecast_transit: [
    ["A busy bus morning", "A transit planner could estimate future ridership from route history, weather and the university calendar."],
    ["Event traffic", "A Raleigh planner could forecast traffic volume around an event to prepare transport services; forecasting alone would not choose routes."],
  ],
  generator_base: [
    ["Drafting an invitation", "A generator could create invitation text from a few instructions about an event’s audience and tone."],
    ["Making a concept image", "A tool could create a new image from a description, rather than find an existing photo."],
  ],
  generator_catalog: [
    ["A clearer device listing", "A library could draft a consistent equipment description from a device record and official documentation."],
    ["Explaining software uses", "A catalog editor could generate draft example uses from verified software documentation, then check each claim."],
  ],
  generator_classroom_chatbot: [
    ["A student-made study bot", "A class could build a chatbot with a defined topic, audience and knowledge boundaries, then test its responses."],
    ["Practicing dialogue rules", "Students could configure a bot for language practice and evaluate whether it follows their conversation rules."],
  ],
  generator_conversational: [
    ["Planning through conversation", "An assistant could ask clarifying questions about a trip and draft a plan from the conversation."],
    ["Explaining a confusing message", "A chat assistant could respond to follow-up questions about a message, while needing the user to check its interpretation."],
  ],
  generator_creative: [
    ["Poster concepts", "An arts group in Durham could generate visual concepts from a brief before a designer selects and edits them."],
    ["A story starter", "A writer could request a new opening scene with specified characters and a mood, then revise the draft."],
  ],
  generator_document: [
    ["Meeting notes to a draft", "A tool could turn supplied notes into a structured draft report for someone to check."],
    ["Rewriting instructions", "A community group could draft a plain-language version of its source instructions while checking that details remain accurate."],
  ],
  generator_learning: [
    ["Practice questions", "A study tool could draft questions from a supplied chapter for a learner or teacher to check."],
    ["Another explanation", "A learner could request an explanation with a new example based on course material, while checking it against the source."],
  ],
  generator_lesson_planner: [
    ["A lesson outline", "A teacher could draft activities from a grade level, classroom context and learning goals, then adapt them for students."],
    ["Planning from class needs", "A teacher could use a summary of class performance to request lesson-plan components that address specific gaps."],
  ],
  recommender_adaptive_learning: [
    ["Feedback during a learning game", "A game could use a learner’s responses to select tailored feedback about the current challenge."],
    ["Responding to a group", "An educational game could adapt its guidance to patterns in group activity, with teachers checking whether the adaptation helps."],
  ],
  recommender_ai_curator: [
    ["Exploring an exhibition theme", "A curator could use collection records and a prompt to propose artworks that fit a theme, then review the selections."],
    ["Planning a gallery arrangement", "An exhibition team could request installation suggestions from museum records, then check physical and curatorial constraints."],
  ],
  recommender_base: [
    ["Local exploration", "A guide could rank Durham or Raleigh activities using someone’s stated interests and previous choices."],
    ["Personal suggestions", "A service could use interactions and item descriptions to rank choices a person may enjoy."],
  ],
  recommender_content: [
    ["Finding the next song", "A music service could use listening patterns to rank tracks a listener may enjoy."],
    ["Choosing a film", "A streaming guide could use viewing history and film descriptions to suggest what to watch next."],
  ],
  recommender_learning: [
    ["What to study next", "A course tool could rank practice resources using a learner’s progress and interests."],
    ["A useful tutorial", "A university study guide could suggest an available tutorial that addresses a student’s recent mistakes."],
  ],
  recommender_menu: [
    ["Choosing lunch", "A restaurant tool could rank dishes using stated preferences, dietary constraints and previous orders."],
    ["Trying something different", "A Durham dining guide could suggest unfamiliar menu items related to foods a diner already likes."],
  ],
  recommender_product: [
    ["Related purchases", "An online shop could rank items using browsing history, past purchases and product descriptions."],
    ["A new hobby", "A store could suggest beginner supplies related to a shopper’s recent interests, rather than only matching a search phrase."],
  ],
  recommender_research: [
    ["Sources for an essay", "A writing tool could suggest academic papers based on a student’s draft and thesis statement."],
    ["Broadening a reading list", "A researcher could use an outline to request related publications, then assess each source’s relevance."],
  ],
  retriever_base: [
    ["Finding a help article", "A search tool could rank existing help pages that answer a question about a device."],
    ["Searching a community archive", "A resident could enter a query to find relevant existing documents, rather than generate a new account of events."],
  ],
  retriever_knowledge: [
    ["Finding a workplace policy", "An internal search tool could return passages from an organization’s existing leave policy."],
    ["Looking up a repair step", "A technician could search indexed manuals for the section relevant to an equipment question."],
  ],
  retriever_product: [
    ["Searching for a raincoat", "A catalog search could return existing products matching a shopper’s request for a lightweight waterproof coat."],
    ["Finding a compatible part", "A shop search could rank listed parts that match a requested model and specifications."],
  ],
  retriever_records: [
    ["Looking up a permit", "A civic search tool could retrieve existing permit records relevant to a resident’s query."],
    ["Finding an ordinance", "A Raleigh or Durham resident could search public documents for relevant rules, then read the official text."],
  ],
  retriever_research: [
    ["Starting a literature search", "A university student could search indexed scholarly papers with a research question and compare the ranked results."],
    ["Finding a specific study", "A research search tool could retrieve existing papers from keywords about a method and topic."],
  ],
  retriever_semantic_search: [
    ["Searching with a question", "An academic tool could turn a natural-language research question into structured searches and related concepts."],
    ["Finding different wording", "A literature tool could retrieve papers about the meaning of a research concept even when their wording differs from the query."],
  ],
  scheduler_base: [
    ["Booking shared equipment", "A university tool could assign equipment time slots while respecting availability and booking constraints."],
    ["Planning volunteer work", "An organizer could assign jobs and times using volunteer availability and task requirements."],
  ],
  scheduler_delivery: [
    ["A delivery round", "A Raleigh business could order delivery stops using destinations, travel times and promised arrival windows."],
    ["Loading the right van", "A delivery planner could assign orders to vehicles while respecting capacity and route constraints."],
  ],
  scheduler_hospital: [
    ["Sharing clinical equipment", "A hospital planner could assign equipment and appointment slots while respecting patient needs and availability."],
    ["Planning bed assignments", "A care operations tool could propose resource assignments from available beds and staff for people to review."],
  ],
  scheduler_ride_booking: [
    ["Requesting a ride", "A booking assistant could collect pickup, destination and requested time to prepare a scheduled trip confirmation."],
    ["Checking trip details", "An assistant could clarify a rider’s requested return time before confirming booking details, without inventing an available ride."],
  ],
  scheduler_traffic_signal: [
    ["Studying a junction", "A city tool could measure traffic from live camera video to inform signal-timing decisions."],
    ["Reviewing crossing safety", "A traffic team could use video-derived measurements to study patterns at a crossing; the measurements alone would not guarantee safety."],
  ],
  scheduler_transit: [
    ["Assigning buses", "A transit planner could assign vehicles to routes using schedules, demand and operating constraints."],
    ["Responding to a delay", "A dispatcher could compare vehicle positions and traffic conditions to choose a timing adjustment."],
  ],
  scheduler_transit_flow: [
    ["A late bus approaching a signal", "A transit tool could combine bus GPS and schedule data to support a signal-priority decision."],
    ["Improving a corridor", "A Durham planning team could use on-time performance data to propose operational changes intended to reduce bus delays."],
  ],
  scheduler_workforce: [
    ["A café rota", "A café could assign shifts from expected demand, worker availability and required skills."],
    ["Staffing a cultural venue", "A venue could build a staffing schedule that respects worker preferences and labor rules while covering busy periods."],
  ],
};

export const everydayExamples: EverydayExamples = Object.fromEntries(
  Object.entries(examples).map(([id, items]) => [id, items.map(([title, description]) =>
    ({ title, description, illustrative: true }))]),
);
