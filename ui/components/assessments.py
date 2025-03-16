# ui/components/assessment.py

import streamlit as st
import pandas as pd
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from config.logging_config import get_module_logger
from ui.state_manager import state_manager
from ui.components.common import display_error, display_success, display_info
from core.assessment.assessment_processor import AssessmentProcessor
from core.assessment.student_profile_manager import StudentProfileManager
from core.assessment.report_generator import ReportGenerator

# Create a logger for this module
logger = get_module_logger("assessment_component")

def render_assessment_tab(app_components: Dict[str, Any]):
    """Render the assessment tab with all assessment-related functionality.
    
    Args:
        app_components: Dictionary with application components
    """
    st.header("Assessment & Knowledge Tracking")
    
    # Initialize components if not already present
    initialize_assessment_components(app_components)
    
    # Create tabs for different assessment functions
    assessment_tabs = st.tabs([
        "Assessment Manager", 
        "Record Responses", 
        "Student Profiles", 
        "Knowledge Dashboard"
    ])
    
    with assessment_tabs[0]:
        render_assessment_manager(app_components)
    
    with assessment_tabs[1]:
        render_response_recorder(app_components)
    
    with assessment_tabs[2]:
        render_student_profiles(app_components)
    
    with assessment_tabs[3]:
        render_knowledge_dashboard(app_components)

def initialize_assessment_components(app_components: Dict[str, Any]):
    """Initialize assessment components if not already present.
    
    Args:
        app_components: Dictionary with application components
    """
    if "assessment_processor" not in app_components:
        app_components["assessment_processor"] = AssessmentProcessor()
    
    if "student_profile_manager" not in app_components:
        app_components["student_profile_manager"] = StudentProfileManager()
    
    if "report_generator" not in app_components:
        app_components["report_generator"] = ReportGenerator()

def render_assessment_manager(app_components: Dict[str, Any]):
    """Render the assessment management interface.
    
    Args:
        app_components: Dictionary with application components
    """
    st.subheader("Assessment Management")
    
    # Get assessment processor
    assessment_processor = app_components["assessment_processor"]
    
    # Create columns for layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Create Assessment")
        
        with st.form("create_assessment_form"):
            assessment_title = st.text_input("Assessment Title", key="assessment_title")
            subject = st.selectbox(
                "Subject",
                ["Mathematics", "Reading", "Science", "Social Studies"],
                key="assessment_subject"
            )
            grade_level = st.text_input("Grade Level", key="assessment_grade")
            
            # Question builder
            st.markdown("#### Add Questions")
            
            # Initialize question list in session state if needed
            if "temp_questions" not in st.session_state:
                st.session_state.temp_questions = []
            
            # Display existing questions
            if st.session_state.temp_questions:
                st.markdown("**Current Questions:**")
                for i, q in enumerate(st.session_state.temp_questions):
                    st.markdown(f"{i+1}. {q.get('text', '')}")
            
            # Question form elements
            question_text = st.text_area("Question Text")
            question_type = st.selectbox(
                "Question Type",
                ["multiple_choice", "true_false", "fill_in", "numeric"]
            )
            
            # Type-specific inputs
            if question_type == "multiple_choice":
                options = st.text_area("Options (one per line)")
                correct_option = st.text_input("Correct Option")
                
            elif question_type == "true_false":
                correct_answer = st.selectbox("Correct Answer", ["True", "False"])
                
            elif question_type == "fill_in":
                correct_answer = st.text_input("Correct Answer")
                
            elif question_type == "numeric":
                correct_answer = st.number_input("Correct Answer", format="%f")
                tolerance = st.number_input("Tolerance", format="%f", value=0.001)
            
            # Form buttons
            col1, col2 = st.columns(2)
            with col1:
                add_question = st.form_submit_button("Add Question")
            with col2:
                create_assessment = st.form_submit_button("Create Assessment")
            
            # Handle add question
            if add_question and question_text:
                # Create question object
                question = {
                    "question_id": str(uuid.uuid4()),
                    "text": question_text,
                    "question_type": question_type
                }
                
                # Add type-specific fields
                if question_type == "multiple_choice":
                    question["options"] = [opt.strip() for opt in options.split("\n") if opt.strip()]
                    question["correct_answer"] = correct_option
                
                elif question_type == "true_false":
                    question["correct_answer"] = correct_answer == "True"
                
                elif question_type == "fill_in":
                    question["correct_answer"] = correct_answer
                
                elif question_type == "numeric":
                    question["correct_answer"] = float(correct_answer)
                    question["tolerance"] = float(tolerance)
                
                # Process question to identify components
                processed_question = assessment_processor._process_question(
                    question, subject, grade_level
                )
                
                # Add to temporary questions list
                st.session_state.temp_questions.append(processed_question)
                st.rerun()
            
            # Handle create assessment
            if create_assessment and assessment_title and st.session_state.temp_questions:
                # Create assessment object
                assessment = {
                    "assessment_id": str(uuid.uuid4()),
                    "title": assessment_title,
                    "subject": subject,
                    "grade_level": grade_level,
                    "questions": st.session_state.temp_questions,
                    "created_at": datetime.now().isoformat()
                }
                
                # Process assessment
                processed_assessment = assessment_processor.process_assessment(assessment)
                
                # Save to state
                assessments = state_manager.get("assessments", [])
                assessments.append(processed_assessment)
                state_manager.set("assessments", assessments)
                
                # Clear temporary questions
                st.session_state.temp_questions = []
                
                display_success(f"Assessment '{assessment_title}' created successfully!")
                st.rerun()
    
    with col2:
        st.markdown("### Existing Assessments")
        
        # Get assessments from state
        assessments = state_manager.get("assessments", [])
        
        if not assessments:
            st.info("No assessments available. Create one to get started.")
        else:
            # Create selection dropdown
            assessment_ids = [a.get("assessment_id") for a in assessments]
            assessment_titles = [a.get("title", "Untitled") for a in assessments]
            
            selected_index = st.selectbox(
                "Select Assessment",
                range(len(assessments)),
                format_func=lambda i: assessment_titles[i]
            )
            
            # Display selected assessment
            selected_assessment = assessments[selected_index]
            
            st.markdown(f"**Title:** {selected_assessment.get('title', 'Untitled')}")
            st.markdown(f"**Subject:** {selected_assessment.get('subject', 'Not specified')}")
            st.markdown(f"**Grade Level:** {selected_assessment.get('grade_level', 'Not specified')}")
            st.markdown(f"**Questions:** {len(selected_assessment.get('questions', []))}")
            
            # Show questions
            with st.expander("View Questions"):
                for i, question in enumerate(selected_assessment.get("questions", [])):
                    st.markdown(f"**Question {i+1}:** {question.get('text', '')}")
                    st.markdown(f"**Type:** {question.get('question_type', '')}")
                    
                    # Show knowledge components
                    if "knowledge_components" in question and question["knowledge_components"]:
                        st.markdown("**Knowledge Components:**")
                        for kc in question["knowledge_components"]:
                            st.markdown(f"- {kc.get('name', '')}")
                    
                    st.markdown("---")
            
            # Export button
            export_assessment = st.form_submit_button("Export Assessment")
            if export_assessment:
                assessment_json = json.dumps(selected_assessment, indent=2)
                st.download_button(
                    "Download JSON",
                    assessment_json,
                    file_name=f"{selected_assessment.get('title', 'assessment')}.json",
                    mime="application/json"
                )

def render_response_recorder(app_components: Dict[str, Any]):
    """Render interface for recording student responses to assessments.
    
    Args:
        app_components: Dictionary with application components
    """
    st.subheader("Record Assessment Responses")
    
    # Get components
    assessment_processor = app_components["assessment_processor"]
    profile_manager = app_components["student_profile_manager"]
    
    # Select student
    student_profiles = get_student_profiles()
    
    if not student_profiles:
        st.info("No student profiles available. Create a profile in the Student Profiles tab.")
        return
    
    student_names = [p.get("name", f"Student {p.get('student_id', '')}") for p in student_profiles]
    selected_student_index = st.selectbox(
        "Select Student",
        range(len(student_profiles)),
        format_func=lambda i: student_names[i]
    )
    selected_student = student_profiles[selected_student_index]
    
    # Select assessment
    assessments = state_manager.get("assessments", [])
    
    if not assessments:
        st.info("No assessments available. Create an assessment in the Assessment Manager tab.")
        return
    
    assessment_titles = [a.get("title", "Untitled") for a in assessments]
    selected_assessment_index = st.selectbox(
        "Select Assessment",
        range(len(assessments)),
        format_func=lambda i: assessment_titles[i]
    )
    selected_assessment = assessments[selected_assessment_index]
    
    # Display response form
    with st.form("response_form"):
        st.markdown(f"### Recording responses for: {selected_assessment.get('title', 'Untitled')}")
        
        # Initialize responses dict
        responses = {}
        
        # Create input for each question
        for i, question in enumerate(selected_assessment.get("questions", [])):
            question_id = question.get("question_id")
            question_text = question.get("text", "")
            question_type = question.get("question_type", "")
            
            st.markdown(f"**Question {i+1}:** {question_text}")
            
            # Create appropriate input based on question type
            if question_type == "multiple_choice":
                options = question.get("options", [])
                if options:
                    response = st.selectbox(
                        f"Answer for Question {i+1}",
                        options=options,
                        key=f"q_{question_id}"
                    )
                    responses[question_id] = response
                else:
                    st.warning("This question has no options defined.")
            
            elif question_type == "true_false":
                response = st.selectbox(
                    f"Answer for Question {i+1}",
                    options=["True", "False"],
                    key=f"q_{question_id}"
                )
                responses[question_id] = response == "True"
            
            elif question_type == "fill_in":
                response = st.text_input(
                    f"Answer for Question {i+1}",
                    key=f"q_{question_id}"
                )
                responses[question_id] = response
            
            elif question_type == "numeric":
                response = st.number_input(
                    f"Answer for Question {i+1}",
                    key=f"q_{question_id}"
                )
                responses[question_id] = float(response)
            
            st.markdown("---")
        
        # Submit button
        submit_button = st.form_submit_button("Submit Responses")
        
        if submit_button:
            # Process each response
            student_id = selected_student.get("student_id")
            assessment_id = selected_assessment.get("assessment_id")
            successful_updates = 0
            
            for question_id, response in responses.items():
                # Find matching question
                question = next(
                    (q for q in selected_assessment.get("questions", []) 
                     if q.get("question_id") == question_id),
                    None
                )
                
                if not question:
                    continue
                
                # Process response
                trace = assessment_processor.process_student_response(
                    student_id, question, response
                )
                
                # Add assessment ID to interaction
                if "interaction" in trace:
                    trace["interaction"]["assessment_id"] = assessment_id
                
                # Update student profile
                if "error" not in trace:
                    profile_manager.update_profile_with_trace(student_id, trace)
                    successful_updates += 1
            
            # Display success message
            if successful_updates > 0:
                display_success(f"Recorded {successful_updates} responses for {selected_student.get('name', 'student')}")
            else:
                display_error("No responses were successfully recorded")

def render_student_profiles(app_components: Dict[str, Any]):
    """Render student profile management interface.
    
    Args:
        app_components: Dictionary with application components
    """
    st.subheader("Student Profiles")
    
    profile_manager = app_components["student_profile_manager"]
    
    # Create layout columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Create Student")
        
        with st.form("create_student_form"):
            student_name = st.text_input("Student Name")
            grade_level = st.text_input("Grade Level")
            
            create_button = st.form_submit_button("Create Student")
            
            if create_button and student_name:
                # Create unique ID
                student_id = f"student_{uuid.uuid4().hex[:8]}"
                
                # Get initial profile
                profile = profile_manager.get_student_profile(student_id)
                
                # Update with form data
                profile["name"] = student_name
                profile["grade_level"] = grade_level
                
                # Save profile
                profile_key = f"student_profile_{student_id}"
                state_manager.set(profile_key, profile)
                
                display_success(f"Created student profile for {student_name}")
                st.rerun()
        
        # Student selection
        st.markdown("### Select Student")
        
        student_profiles = get_student_profiles()
        
        if not student_profiles:
            st.info("No student profiles available.")
        else:
            student_names = [p.get("name", f"Student {p.get('student_id', '')}") for p in student_profiles]
            selected_student_index = st.selectbox(
                "Select Student",
                range(len(student_profiles)),
                format_func=lambda i: student_names[i]
            )
            
            if st.button("View Student"):
                st.session_state.selected_student_index = selected_student_index
                st.rerun()
    
    with col2:
        # Display selected student profile
        if hasattr(st.session_state, "selected_student_index") and student_profiles:
            selected_student = student_profiles[st.session_state.selected_student_index]
            student_id = selected_student.get("student_id")
            
            st.markdown(f"### Student: {selected_student.get('name', 'Unnamed')}")
            st.markdown(f"**Grade Level:** {selected_student.get('grade_level', 'Not specified')}")
            st.markdown(f"**Created:** {format_datetime(selected_student.get('creation_date', ''))}")
            st.markdown(f"**Last Updated:** {format_datetime(selected_student.get('last_updated', ''))}")
            
            # Knowledge state overview
            knowledge_state = selected_student.get("knowledge_state", {})
            
            if knowledge_state:
                st.markdown("### Knowledge State Overview")
                
                # Prepare data for display
                knowledge_data = []
                for component_id, state in knowledge_state.items():
                    # Format component name
                    component_name = component_id.replace("kc_", "").replace("_", " ").title()
                    
                    # Create data row
                    knowledge_data.append({
                        "Component": component_name,
                        "Mastery": f"{state.get('current_value', 0) * 100:.1f}%",
                        "Last Updated": format_datetime(state.get("last_updated", ""))
                    })
                
                # Sort by mastery (highest first)
                knowledge_data.sort(key=lambda x: float(x["Mastery"].replace("%", "")), reverse=True)
                
                # Display as table
                st.dataframe(pd.DataFrame(knowledge_data))
                
                # Overall metrics
                metrics = selected_student.get("metrics", {})
                overall_mastery = metrics.get("overall_mastery", 0) * 100
                
                st.markdown(f"**Overall Mastery:** {overall_mastery:.1f}%")
                st.progress(overall_mastery / 100)
            else:
                st.info("No knowledge data available for this student yet.")
            
            # Assessment history
            interaction_history = selected_student.get("interaction_history", [])
            
            if interaction_history:
                st.markdown("### Assessment History")
                
                # Group by assessment
                assessment_data = {}
                for interaction in interaction_history:
                    assessment_id = interaction.get("assessment_id")
                    if not assessment_id:
                        continue
                    
                    if assessment_id not in assessment_data:
                        assessment_data[assessment_id] = {
                            "interactions": [],
                            "correct_count": 0,
                            "total_count": 0,
                            "last_updated": ""
                        }
                    
                    assessment_data[assessment_id]["interactions"].append(interaction)
                    assessment_data[assessment_id]["total_count"] += 1
                    if interaction.get("is_correct", False):
                        assessment_data[assessment_id]["correct_count"] += 1
                    
                    # Track latest timestamp
                    timestamp = interaction.get("timestamp", "")
                    if timestamp > assessment_data[assessment_id]["last_updated"]:
                        assessment_data[assessment_id]["last_updated"] = timestamp
                
                # Get assessment titles
                assessments = state_manager.get("assessments", [])
                assessment_map = {a.get("assessment_id"): a.get("title", "Untitled") for a in assessments}
                
                # Prepare data for display
                history_data = []
                for assessment_id, data in assessment_data.items():
                    history_data.append({
                        "Assessment": assessment_map.get(assessment_id, "Unknown"),
                        "Score": f"{data['correct_count']}/{data['total_count']}",
                        "Percentage": f"{(data['correct_count'] / max(data['total_count'], 1)) * 100:.1f}%",
                        "Completed": format_datetime(data["last_updated"])
                    })
                
                # Sort by most recent
                history_data.sort(key=lambda x: x["Completed"], reverse=True)
                
                # Display as table
                st.dataframe(pd.DataFrame(history_data))
            else:
                st.info("No assessment history available for this student.")
            
            # Generate report button
            if interaction_history and st.button("Generate Assessment Report"):
                render_assessment_report(app_components, student_id)

def render_knowledge_dashboard(app_components: Dict[str, Any]):
    """Render knowledge dashboard interface.
    
    Args:
        app_components: Dictionary with application components
    """
    st.subheader("Knowledge Dashboard")
    
    profile_manager = app_components["student_profile_manager"]
    
    # Get student profiles
    student_profiles = get_student_profiles()
    
    if not student_profiles:
        st.info("No student profiles available.")
        return
    
    # Student selection
    student_names = [p.get("name", f"Student {p.get('student_id', '')}") for p in student_profiles]
    selected_student_index = st.selectbox(
        "Select Student",
        range(len(student_profiles)),
        format_func=lambda i: student_names[i]
    )
    selected_student = student_profiles[selected_student_index]
    student_id = selected_student.get("student_id")
    
    # Subject filter
    subjects = ["All Subjects", "Mathematics", "Reading", "Science", "Social Studies"]
    selected_subject = st.selectbox("Subject Filter", subjects)
    
    # Get knowledge state
    if selected_subject == "All Subjects":
        knowledge_state = profile_manager.get_student_knowledge_state(student_id)
    else:
        knowledge_state = profile_manager.get_student_knowledge_state(student_id, selected_subject)
    
    if not knowledge_state:
        st.info(f"No knowledge data available for {selected_student.get('name', 'this student')}.")
        return
    
    # Prepare data for visualization
    component_data = []
    for component_id, mastery in knowledge_state.items():
        component_name = component_id.replace("kc_", "").replace("_", " ").title()
        component_data.append({
            "Component": component_name,
            "Mastery": mastery * 100
        })
    
    # Sort by mastery (ascending for bar chart)
    component_data.sort(key=lambda x: x["Mastery"])
    
    # Create DataFrame
    df = pd.DataFrame(component_data)
    
    # Mastery visualization
    st.markdown("### Knowledge Mastery Levels")
    st.bar_chart(df.set_index("Component"))
    
    # Mastery categories
    st.markdown("### Mastery Categories")
    
    # Group by mastery level
    mastery_categories = {
        "Expert (90%+)": [],
        "Proficient (80-90%)": [],
        "Developing (70-80%)": [],
        "Basic (50-70%)": [],
        "Novice (0-50%)": []
    }
    
    for component in component_data:
        mastery = component["Mastery"]
        component_name = component["Component"]
        
        if mastery >= 90:
            mastery_categories["Expert (90%+)"].append(component_name)
        elif mastery >= 80:
            mastery_categories["Proficient (80-90%)"].append(component_name)
        elif mastery >= 70:
            mastery_categories["Developing (70-80%)"].append(component_name)
        elif mastery >= 50:
            mastery_categories["Basic (50-70%)"].append(component_name)
        else:
            mastery_categories["Novice (0-50%)"].append(component_name)
    
    # Create columns for categories
    cols = st.columns(5)
    
    for i, (category, components) in enumerate(mastery_categories.items()):
        with cols[i]:
            st.markdown(f"**{category}**")
            if components:
                for component in components:
                    st.markdown(f"- {component}")
            else:
                st.markdown("None")
    
    # Learning recommendations
    st.markdown("### Learning Recommendations")
    
    # Get recommendations
    subject_filter = None if selected_subject == "All Subjects" else selected_subject
    recommendations = profile_manager.get_learning_recommendations(student_id, subject_filter)
    
    if not recommendations:
        st.success("No recommendations needed! All skills at mastery level.")
    else:
        # Group by priority
        priority_groups = {
            "high": [],
            "medium": [],
            "low": []
        }
        
        for rec in recommendations:
            priority = rec.get("priority", "low")
            priority_groups[priority].append(rec)
        
        # Display high priority recommendations
        if priority_groups["high"]:
            st.markdown("#### High Priority Focus Areas")
            for rec in priority_groups["high"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{rec['component_name']}**")
                    st.progress(rec["mastery"])
                with col2:
                    st.markdown(f"**Mastery:** {rec['mastery']*100:.1f}%")
                st.markdown(f"{rec['recommendation']}")
                st.markdown("---")
        
        # Display medium and low priority in expandable sections
        if priority_groups["medium"]:
            with st.expander("Medium Priority Areas"):
                for rec in priority_groups["medium"]:
                    st.markdown(f"**{rec['component_name']}** - {rec['mastery']*100:.1f}%")
                    st.progress(rec["mastery"])
        
        if priority_groups["low"]:
            with st.expander("Low Priority Areas"):
                for rec in priority_groups["low"]:
                    st.markdown(f"**{rec['component_name']}** - {rec['mastery']*100:.1f}%")
                    st.progress(rec["mastery"])

def render_assessment_report(app_components: Dict[str, Any], student_id: str):
    """Render assessment report.
    
    Args:
        app_components: Dictionary with application components
        student_id: Student identifier
    """
    # Get components
    profile_manager = app_components["student_profile_manager"]
    report_generator = app_components["report_generator"]
    
    # Get student profile
    profile = profile_manager.get_student_profile(student_id)
    
    # Get assessments
    assessments = state_manager.get("assessments", [])
    
    # Create assessment selector
    assessment_titles = [a.get("title", "Untitled") for a in assessments]
    selected_assessment_index = st.selectbox(
        "Select Assessment for Report",
        range(len(assessments)),
        format_func=lambda i: assessment_titles[i]
    )
    selected_assessment = assessments[selected_assessment_index]
    assessment_id = selected_assessment.get("assessment_id")

# Get interactions for this assessment
    interaction_history = profile.get("interaction_history", [])
    assessment_interactions = [i for i in interaction_history if i.get("assessment_id") == assessment_id]
    
    if not assessment_interactions:
        st.warning("No interaction data found for this assessment and student.")
        return
    
    # Get knowledge state
    knowledge_state = profile_manager.get_student_knowledge_state(student_id)
    
    # Generate report
    report = report_generator.generate_report(
        student_id,
        selected_assessment,
        assessment_interactions,
        knowledge_state
    )
    
    # Display report
    st.markdown(f"## Assessment Report: {report.get('assessment_title', 'Untitled')}")
    st.markdown(f"**Student:** {profile.get('name', 'Unnamed')}")
    st.markdown(f"**Generated:** {format_datetime(report.get('generated_at', ''))}")
    
    # Display overall performance
    overall = report.get("overall_performance", {})
    if overall:
        st.markdown("### Overall Performance")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Score", f"{overall.get('correct_count', 0)}/{overall.get('total_questions', 0)}")
        with col2:
            st.metric("Percentage", f"{overall.get('percentage', 0):.1f}%")
        with col3:
            st.metric("Grade", overall.get("grade", "N/A"))
        
        # Progress bar
        st.progress(overall.get('percentage', 0) / 100)
    
    # Display question performance
    question_performance = report.get("question_performance", [])
    if question_performance:
        st.markdown("### Question Performance")
        
        for i, question in enumerate(question_performance):
            with st.expander(f"Question {i+1}: {question.get('text', '')}"):
                st.markdown(f"**Result:** {'✓ Correct' if question.get('is_correct', False) else '✗ Incorrect'}")
                
                # Show cognitive skills
                if question.get("cognitive_skills"):
                    st.markdown(f"**Cognitive Skills:** {', '.join(question['cognitive_skills'])}")
                
                # Show knowledge components
                if question.get("knowledge_components"):
                    st.markdown("**Knowledge Components:**")
                    for kc in question["knowledge_components"]:
                        st.markdown(f"- {kc.get('name', '')}")
    
    # Display knowledge component analysis
    components = report.get("knowledge_components", [])
    if components:
        st.markdown("### Knowledge Component Analysis")
        
        # Prepare data for display
        component_data = []
        for component in components:
            component_data.append({
                "Component": component.get("name", "Unknown"),
                "Mastery": f"{component.get('mastery', 0) * 100:.1f}%",
                "Level": component.get("mastery_level", "Unknown")
            })
        
        # Display as table
        st.dataframe(pd.DataFrame(component_data))
    
    # Display recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        st.markdown("### Learning Recommendations")
        
        for recommendation in recommendations:
            st.markdown(f"**Focus Area:** {recommendation.get('component_name', '')}")
            st.markdown(f"**Current Mastery:** {recommendation.get('current_mastery', 0) * 100:.1f}%")
            st.markdown(f"**Target:** {recommendation.get('target_mastery', 0) * 100:.1f}%")
            st.progress(recommendation.get('current_mastery', 0) / recommendation.get('target_mastery', 1))
            st.markdown(f"**Recommendation:** {recommendation.get('recommendation', '')}")
            st.markdown("---")
    
    # Export button
    if st.button("Export Report"):
        report_json = json.dumps(report, indent=2)
        st.download_button(
            "Download Report JSON",
            report_json,
            file_name=f"assessment_report_{report.get('assessment_title', 'untitled').replace(' ', '_').lower()}.json",
            mime="application/json"
        )

def get_student_profiles() -> List[Dict[str, Any]]:
    """Get all student profiles from state.
    
    Returns:
        List of student profile dictionaries
    """
    profiles = []
    
    # Get all keys that match the profile pattern
    for key in state_manager.storage.list_keys():
        if key.startswith("student_profile_"):
            # Extract student ID from key
            student_id = key.replace("student_profile_", "")
            
            # Get profile from state
            profile = state_manager.get(key)
            
            # Add to list if valid
            if profile and "student_id" in profile:
                profiles.append(profile)
    
    return profiles

def format_datetime(timestamp: str) -> str:
    """Format ISO timestamp to readable date/time.
    
    Args:
        timestamp: ISO format timestamp
        
    Returns:
        Formatted date/time string
    """
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return timestamp