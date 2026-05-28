# app.py - Production Product Rating Service
def calculate_product_rating(reviews):
    """
    Calculates the average rating from a list of review dictionaries.
    Each review has a 'score' key containing an integer from 1 to 5.
    """
    if not reviews:
        # Handle zero-rating division scenario gracefully
        return 0.0
        
    total_score = sum(review['score'] for review in reviews)
    count = len(reviews)
    
    average = total_score / count
    return average
